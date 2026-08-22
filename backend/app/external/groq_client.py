"""Legacy client shim - delegates to unified Gemini LLM client."""
from app.external.llm_client import client, llm

def get_groq_client():
    return client
