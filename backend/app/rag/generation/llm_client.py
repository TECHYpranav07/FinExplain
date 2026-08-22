from typing import Optional, List, Dict, Any
from app.external.llm_client import llm, LLMClient

# Re-export singleton
llm_client = llm
