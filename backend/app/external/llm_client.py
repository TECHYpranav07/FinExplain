"""
Centralized resilient LLM client for FinExplain.
Supports Google Gemini (via LangChain and direct Google Generative AI / REST) and Groq.

Features:
- Primary Google Gemini LLM integration via LangChain ChatGoogleGenerativeAI with REST fallback
- Model and API key sourced directly from backend/.env
- Automatic retry logic with exponential backoff for rate limits (429) and server errors (5xx)
- OpenAI-compatible completion proxy for backward compatibility across all extraction/RAG modules
- Structured logging and usage tracking
"""

import time
import json
import logging
from typing import List, Dict, Any, Optional
from types import SimpleNamespace
import requests

from app.core.config import settings
from app.core.constants import DEFAULT_LLM_MODEL, DEFAULT_GEMINI_MODEL, DEFAULT_GROQ_MODEL

logger = logging.getLogger(__name__)

_groq_instance: Optional[Any] = None


def get_gemini_client(model: Optional[str] = None, temperature: float = 0.1) -> Any:
    """Returns a LangChain ChatGoogleGenerativeAI client instance."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    api_key = settings.effective_gemini_api_key
    if not api_key:
        raise ValueError("GEMINI_API_KEY (or GOOGLE_API_KEY) is not configured in backend/.env.")

    effective_model = model or settings.active_llm_model or DEFAULT_GEMINI_MODEL
    # Strip 'models/' prefix if present
    if effective_model.startswith("models/"):
        effective_model = effective_model[len("models/"):]

    return ChatGoogleGenerativeAI(
        model=effective_model,
        google_api_key=api_key,
        temperature=temperature,
        max_retries=0,  # avoid subdependency keyword argument collision
    )


def get_groq_client() -> Any:
    """Returns singleton Groq client instance if configured."""
    global _groq_instance
    if _groq_instance is None:
        from groq import Groq
        api_key = settings.GROQ_API_KEY
        if not api_key:
            raise ValueError("GROQ_API_KEY is not configured.")
        _groq_instance = Groq(api_key=api_key, timeout=30.0)
    return _groq_instance


class LLMClient:
    """Resilient wrapper for LangChain Gemini and Groq LLM completions with bounded retries."""

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
        Execute a chat completion with automatic provider selection and retries.
        """
        provider = (settings.LLM_PROVIDER or "gemini").lower()
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                if provider == "gemini" or (provider != "groq" and settings.effective_gemini_api_key):
                    return self._call_gemini(
                        messages=messages,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format=response_format,
                    )
                else:
                    return self._call_groq(
                        messages=messages,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format=response_format,
                    )
            except Exception as e:
                last_exception = e
                err_str = str(e).lower()
                # Check for non-retryable errors (invalid API key, auth, bad request)
                if any(x in err_str for x in ["401", "403", "invalid_api_key", "api_key_invalid", "api key not valid"]):
                    logger.error(f"[LLMClient] Non-retryable authentication error ({provider}): {e}")
                    raise e

                if attempt < self.max_retries:
                    sleep_time = self.initial_backoff * (2 ** attempt)
                    logger.warning(
                        f"[LLMClient] Attempt {attempt + 1} ({provider}) failed: {e}. Retrying in {sleep_time:.1f}s..."
                    )
                    time.sleep(sleep_time)
                else:
                    logger.error(f"[LLMClient] All {self.max_retries + 1} attempts failed ({provider}): {e}")

        raise last_exception or RuntimeError(f"LLM request failed for provider {provider}")

    def _call_gemini(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """Invokes Google Gemini with LangChain first, falling back to Google Generative Language REST."""
        api_key = settings.effective_gemini_api_key
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured in backend/.env.")

        target_model = model or settings.active_llm_model or DEFAULT_GEMINI_MODEL
        if target_model.startswith("models/"):
            target_model = target_model[len("models/"):]

        # Strategy 1: LangChain ChatGoogleGenerativeAI
        try:
            from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

            lc_messages = []
            for m in messages:
                role = m.get("role", "user")
                content = m.get("content", "")
                if role == "system":
                    lc_messages.append(SystemMessage(content=content))
                elif role == "assistant":
                    lc_messages.append(AIMessage(content=content))
                else:
                    lc_messages.append(HumanMessage(content=content))

            client_instance = get_gemini_client(model=target_model, temperature=temperature)
            response = client_instance.invoke(lc_messages)

            content = response.content
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, str):
                        text_parts.append(part)
                    elif isinstance(part, dict) and "text" in part:
                        text_parts.append(part["text"])
                    else:
                        text_parts.append(str(part))
                return "\n".join(text_parts).strip()
            return str(content or "").strip()

        except Exception as lc_err:
            logger.warning(f"[LLMClient] LangChain invocation encountered ({lc_err}); falling back to Google REST endpoint...")

        # Strategy 2: Direct Google Generative Language REST API
        return self._call_gemini_rest(
            messages=messages,
            api_key=api_key,
            model=target_model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )

    def _call_gemini_rest(
        self,
        messages: List[Dict[str, str]],
        api_key: str,
        model: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """Direct REST invocation of Google Generative Language API."""
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

        # Gemini requires at least one user message
        if not contents:
            contents.append({"role": "user", "parts": [{"text": "Hello"}]})

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
            # If model name failed with 404, try fallback to default flash model
            if res.status_code == 404 and model != DEFAULT_GEMINI_MODEL:
                logger.warning(f"[LLMClient] Model '{model}' not found (404). Trying default '{DEFAULT_GEMINI_MODEL}'...")
                fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/{DEFAULT_GEMINI_MODEL}:generateContent?key={api_key}"
                res = requests.post(fallback_url, json=payload, timeout=45)

            if not res.ok:
                raise RuntimeError(f"Gemini REST API error ({res.status_code}): {res.text}")

        data = res.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return ""

        parts = candidates[0].get("content", {}).get("parts", [])
        text_parts = [p.get("text", "") for p in parts if isinstance(p, dict)]
        return "".join(text_parts).strip()

    def _call_groq(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """Invokes Groq LLM API."""
        groq_client = get_groq_client()
        groq_model = model or settings.active_llm_model or DEFAULT_GROQ_MODEL

        kwargs: Dict[str, Any] = {
            "model": groq_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        response = groq_client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""


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
