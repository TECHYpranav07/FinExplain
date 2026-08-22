from pydantic import BaseModel
from enum import Enum
from app.rag.generation.generator import client
import json

class QueryIntent(str, Enum):
    COMPARISON = "comparison"
    LOOKUP = "lookup"
    CALCULATION = "calculation"
    GENERAL = "general"

class IntentResult(BaseModel):
    intent: QueryIntent
    confidence: float
    extracted_entities: dict

def classify_intent(query: str) -> IntentResult:
    """
    Classify the user's query intent using Groq LLM.
    """
    prompt = f"""
Classify the following user question about loans into one of these categories:
- comparison: Comparing two or more loan products (e.g., "Which is cheaper?")
- lookup: Looking up a specific term or value (e.g., "What is the APR?")
- calculation: Needing a numerical calculation (e.g., "What's the total cost?")
- general: General questions that don't fit above

Question: "{query}"

Return ONLY a JSON object with:
{{
  "intent": "comparison|lookup|calculation|general",
  "confidence": 0.0-1.0,
  "extracted_entities": {{"field": "value"}}  // e.g., {{"apr": "10.5", "product": "FlexiLoan"}}
}}
"""
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200
        )
        result = json.loads(response.choices[0].message.content)
        return IntentResult(
            intent=QueryIntent(result["intent"]),
            confidence=result["confidence"],
            extracted_entities=result.get("extracted_entities", {})
        )
    except Exception:
        return IntentResult(
            intent=QueryIntent.GENERAL,
            confidence=0.5,
            extracted_entities={}
        )