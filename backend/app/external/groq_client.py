from groq import Groq
from app.core.config import settings
from typing import Optional

_groq_client: Optional[Groq] = None

def get_groq_client() -> Groq:
    """Returns singleton Groq client instance."""
    global _groq_client
    if _groq_client is None:
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not configured.")
        _groq_client = Groq(api_key=settings.GROQ_API_KEY)
    return _groq_client
