from groq import Groq
from app.core.config import settings
from typing import Optional, List, Dict, Any

class LLMClient:
    """Wrapper around Groq API for unified LLM invocations."""
    def __init__(self, api_key: Optional[str] = None):
        key = api_key or settings.GROQ_API_KEY
        self.client = Groq(api_key=key) if key else None
        self.default_model = "openai/gpt-oss-120b"

    def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1000
    ) -> str:
        if not self.client:
            raise ValueError("GROQ_API_KEY is not configured.")
        
        response = self.client.chat.completions.create(
            model=model or self.default_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content

llm_client = LLMClient()
