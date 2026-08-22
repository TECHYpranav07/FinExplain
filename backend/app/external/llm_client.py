"""
Centralized resilient LLM client for FinExplain (FIN-024).

Features:
- Singleton Groq client initialization
- Configurable timeout and bounded retries with exponential backoff for 429/5xx errors
- Fallback handling and structured error reporting
- Token usage tracking
"""

import time
import logging
from typing import List, Dict, Any, Optional
from groq import Groq
from app.core.config import settings
from app.core.constants import DEFAULT_GROQ_MODEL

logger = logging.getLogger(__name__)

_groq_instance: Optional[Groq] = None


def get_groq_client() -> Groq:
    """Returns singleton Groq client instance."""
    global _groq_instance
    if _groq_instance is None:
        api_key = settings.GROQ_API_KEY
        if not api_key:
            raise ValueError("GROQ_API_KEY is not configured.")
        _groq_instance = Groq(api_key=api_key, timeout=30.0)
    return _groq_instance


class LLMClient:
    """Resilient wrapper for Groq LLM completions with bounded retries."""

    def __init__(self, max_retries: int = 2, initial_backoff: float = 1.0):
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = DEFAULT_GROQ_MODEL,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Execute a chat completion with retries on rate limit (429) or server errors (5xx).
        """
        client = get_groq_client()
        last_exception = None

        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        for attempt in range(self.max_retries + 1):
            try:
                response = client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                if response.usage:
                    logger.debug(
                        f"[LLMClient] Usage: prompt_tokens={response.usage.prompt_tokens}, "
                        f"completion_tokens={response.usage.completion_tokens}, total={response.usage.total_tokens}"
                    )
                return content or ""
            except Exception as e:
                last_exception = e
                err_str = str(e)
                # Check for 401/400 (client error/auth failure) - do NOT retry
                if "401" in err_str or "invalid_api_key" in err_str.lower() or "400" in err_str:
                    logger.error(f"[LLMClient] Non-retryable error: {e}")
                    raise e

                if attempt < self.max_retries:
                    sleep_time = self.initial_backoff * (2 ** attempt)
                    logger.warning(
                        f"[LLMClient] Attempt {attempt + 1} failed: {e}. Retrying in {sleep_time:.1f}s..."
                    )
                    time.sleep(sleep_time)
                else:
                    logger.error(f"[LLMClient] All {self.max_retries + 1} attempts failed: {e}")

        raise last_exception or RuntimeError("LLM request failed")


# Global singleton helper
llm = LLMClient()
