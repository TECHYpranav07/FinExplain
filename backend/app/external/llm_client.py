"""
Centralized Gemini LLM client for FinExplain.
Exclusively uses Google Gemini API with configuration sourced from backend/.env.

Features:
- Pure Google Gemini LLM engine (API Key & Model strictly from backend/.env)
- Auto-sanitizes model names (e.g. handles flash-light -> flash-lite, strips models/ prefix)
- Persistent HTTP session for TCP/TLS reuse (saves ~50-100ms per call)
- Fail-fast on 404 (configuration error) — only retries transient 429/5xx
- Startup model validation
- OpenAI-compatible completion proxy (client.chat.completions.create) for unified downstream caller support
- Resilient retry logic with exponential backoff for rate limits (429) and transient server errors (5xx)
- Structured logging
"""

import time
import json
import logging
from typing import List, Dict, Any, Optional
from types import SimpleNamespace
import requests

from app.core.config import settings
from app.core.constants import DEFAULT_GEMINI_MODEL

logger = logging.getLogger(__name__)

import threading

# ---------------------------------------------------------------------------
# Process-wide Gemini API Call Pacer (Strictly <= 14 requests / min)
# ---------------------------------------------------------------------------
_GEMINI_CALL_LOCK = threading.Lock()
_LAST_GEMINI_CALL_TIME = 0.0
_MIN_GEMINI_INTERVAL_SECONDS = 4.2


# ---------------------------------------------------------------------------
# Persistent HTTP session — reuses TCP connections and TLS handshakes
# ---------------------------------------------------------------------------
_http_session: Optional[requests.Session] = None


def _get_http_session() -> requests.Session:
    """Return a persistent HTTP session for Gemini API calls."""
    global _http_session
    if _http_session is None:
        _http_session = requests.Session()
        _http_session.headers.update({"Content-Type": "application/json"})
    return _http_session


def _sanitize_model_name(raw_model: Optional[str]) -> str:
    """Sanitizes model name from .env or caller arguments."""
    model = (raw_model or settings.GEMINI_MODEL or DEFAULT_GEMINI_MODEL).strip()
    
    # Strip 'models/' prefix if present
    if model.startswith("models/"):
        model = model[len("models/"):]
        
    # Auto-correct common typos
    if "flash-light" in model.lower():
        model = model.replace("flash-light", "flash-lite").replace("FLASH-LIGHT", "flash-lite")
        
    # Ignore non-gemini model names passed by old callers
    if "/" in model or "gpt" in model.lower() or "llama" in model.lower():
        model = settings.GEMINI_MODEL or DEFAULT_GEMINI_MODEL
        if model.startswith("models/"):
            model = model[len("models/"):]
        if "flash-light" in model.lower():
            model = model.replace("flash-light", "flash-lite").replace("FLASH-LIGHT", "flash-lite")

    return model


def validate_model(model: Optional[str] = None) -> bool:
    """
    Validate that the configured Gemini model exists on the API.
    Call this at application startup to fail fast on misconfiguration.
    Returns True if valid, raises RuntimeError if not.
    """
    api_key = settings.effective_gemini_api_key
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured in backend/.env")

    target_model = _sanitize_model_name(model)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}?key={api_key}"

    try:
        session = _get_http_session()
        res = session.get(url, timeout=10)
        if res.ok:
            logger.info(f"[LLMClient] ✅ Model '{target_model}' validated successfully")
            return True
        elif res.status_code == 404:
            raise RuntimeError(
                f"Gemini model '{target_model}' does not exist (404). "
                f"Check GEMINI_MODEL in backend/.env. "
                f"Available models: gemini-2.5-flash, gemini-2.5-pro, gemini-2.0-flash"
            )
        else:
            logger.warning(f"[LLMClient] Model validation returned {res.status_code}: {res.text[:200]}")
            return True  # Non-404 errors might be transient
    except requests.RequestException as e:
        logger.warning(f"[LLMClient] Model validation network error (non-fatal): {e}")
        return True  # Network errors during startup are non-fatal


# Retryable HTTP status codes (transient failures only)
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class LLMClient:
    """Resilient Google Gemini LLM completions client."""

    def __init__(self, max_retries: int = 3, initial_backoff: float = 2.0):
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Execute a chat completion with Google Gemini using configuration from backend/.env.
        """
        api_key = settings.effective_gemini_api_key
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is not configured in backend/.env. "
                "Please add GEMINI_API_KEY=your_key to backend/.env."
            )

        target_model = _sanitize_model_name(model)
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return self._invoke_gemini(
                    messages=messages,
                    api_key=api_key,
                    model=target_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )
            except Exception as e:
                last_exception = e
                err_str = str(e).lower()

                # Fail fast on non-retryable auth / bad API key errors
                if any(x in err_str for x in ["api_key_invalid", "api key not valid", "401", "403"]):
                    logger.error(f"[LLMClient] Non-retryable API key error: {e}")
                    raise e

                # Fail fast on 404 — this is a configuration error, not transient
                if "404" in err_str and "not found" in err_str:
                    logger.error(
                        f"[LLMClient] Model '{target_model}' not found (404). "
                        f"Fix GEMINI_MODEL in backend/.env. Not retrying."
                    )
                    raise e

                # A daily/project quota cannot recover within this request.
                # Retrying it blocks the whole RAG query and can make a
                # benchmark hang for several minutes without changing the
                # outcome. Transient per-minute 429s still use backoff below.
                if any(
                    marker in err_str
                    for marker in (
                        "generaterequestsperday",
                        "daily quota",
                    )
                ):
                    logger.error(f"[LLMClient] Daily quota exhausted; failing fast: {e}")
                    raise e

                if attempt < self.max_retries:
                    # Dynamically parse retryDelay from Gemini 429 quota failure
                    import re
                    retry_match = re.search(r'retry in ([\d\.]+)s', err_str) or re.search(r'"retrydelay":\s*"([\d\.]+)s"', err_str)
                    if retry_match:
                        sleep_time = float(retry_match.group(1)) + 1.5
                    elif "429" in err_str or "resource_exhausted" in err_str:
                        sleep_time = max(5.0 * (2 ** attempt), self.initial_backoff * (2 ** attempt))
                    else:
                        sleep_time = self.initial_backoff * (2 ** attempt)

                    logger.warning(
                        f"[LLMClient] Attempt {attempt + 1} failed: {e}. Retrying in {sleep_time:.1f}s..."
                    )
                    time.sleep(sleep_time)
                else:
                    logger.error(f"[LLMClient] All {self.max_retries + 1} attempts failed: {e}")

        raise last_exception or RuntimeError(f"Gemini LLM request failed for model '{target_model}'.")

    def _invoke_gemini(
        self,
        messages: List[Dict[str, str]],
        api_key: str,
        model: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """Invokes Google Generative Language REST API directly."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        system_instruction = None
        contents = []

        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content}]})
            else:
                contents.append({"role": "user", "parts": [{"text": content}]})

        # Gemini requires at least one user content item
        if not contents:
            contents.append({"role": "user", "parts": [{"text": "Process loan request."}]})

        generation_config: Dict[str, Any] = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }
        if response_format and response_format.get("type") == "json_object":
            generation_config["responseMimeType"] = "application/json"

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": generation_config,
        }
        if system_instruction:
            payload["system_instruction"] = system_instruction

        global _LAST_GEMINI_CALL_TIME
        with _GEMINI_CALL_LOCK:
            now = time.time()
            elapsed = now - _LAST_GEMINI_CALL_TIME
            if elapsed < _MIN_GEMINI_INTERVAL_SECONDS:
                time.sleep(_MIN_GEMINI_INTERVAL_SECONDS - elapsed)
            _LAST_GEMINI_CALL_TIME = time.time()

        session = _get_http_session()
        res = session.post(url, json=payload, timeout=45)

        if not res.ok:
            raise RuntimeError(f"Gemini API error ({res.status_code}): {res.text}")

        data = res.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return ""

        parts = candidates[0].get("content", {}).get("parts", [])
        text_parts = [p.get("text", "") for p in parts if isinstance(p, dict)]
        return "".join(text_parts).strip()


# Global singleton helper
llm = LLMClient()


class _OpenAICompatChat:
    """Provides a `.completions.create(...)` proxy to `llm.chat_completion(...)`."""

    class _Completions:
        def create(self, **kwargs) -> Any:
            messages = kwargs.get("messages", [])
            model = kwargs.get("model")
            temperature = kwargs.get("temperature", 0.1)
            max_tokens = kwargs.get("max_tokens", 2048)
            response_format = kwargs.get("response_format")

            content = llm.chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )

            message_obj = SimpleNamespace(content=content)
            choice_obj = SimpleNamespace(message=message_obj, index=0, finish_reason="stop")
            return SimpleNamespace(
                choices=[choice_obj],
                usage=SimpleNamespace(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            )

    completions = _Completions()


class OpenAICompatProxy:
    """Unified client proxy mimicking standard chat completions API."""
    chat = _OpenAICompatChat()


# Compatibility client instance for modules importing `client`
client = OpenAICompatProxy()
