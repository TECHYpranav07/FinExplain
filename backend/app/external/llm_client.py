"""
Centralized Gemini LLM client for FinExplain.
Exclusively uses Google Gemini API with configuration sourced from backend/.env.

Features:
- Pure Google Gemini LLM engine (API Key & Model strictly from backend/.env)
- Auto-sanitizes model names (e.g. fixes common typos like flash-light -> flash-lite, strips models/ prefix)
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


def _sanitize_model_name(raw_model: Optional[str]) -> str:
    """Sanitizes model name from .env or caller arguments."""
    model = (raw_model or settings.GEMINI_MODEL or DEFAULT_GEMINI_MODEL).strip()
    
    # Strip 'models/' prefix if present
    if model.startswith("models/"):
        model = model[len("models/"):]
        
    # Auto-correct common typos
    if "flash-light" in model.lower():
        model = model.replace("flash-light", "flash-lite").replace("FLASH-LIGHT", "flash-lite")
        
    # Ignore legacy groq/openai model names passed by old callers
    if "/" in model or "gpt" in model.lower() or "llama" in model.lower():
        model = settings.GEMINI_MODEL or DEFAULT_GEMINI_MODEL
        if model.startswith("models/"):
            model = model[len("models/"):]
        if "flash-light" in model.lower():
            model = model.replace("flash-light", "flash-lite").replace("FLASH-LIGHT", "flash-lite")

    return model


class LLMClient:
    """Resilient Google Gemini LLM completions client."""

    def __init__(self, max_retries: int = 2, initial_backoff: float = 1.0):
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

                # If model is 404 Not Found, log detailed guidance and fail
                if "404" in err_str and "not found" in err_str:
                    logger.error(
                        f"[LLMClient] Model '{target_model}' not found on Google Gemini API. "
                        f"Check GEMINI_MODEL in backend/.env (e.g. gemini-2.5-flash, gemini-3.5-flash-lite, gemini-2.0-flash)."
                    )
                    raise e

                if attempt < self.max_retries:
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

        res = requests.post(url, json=payload, timeout=45)
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
