from pydantic import BaseModel
from enum import Enum
from app.rag.generation.generator import client
import json
import re

class QueryIntent(str, Enum):
    COMPARISON = "comparison"
    LOOKUP = "lookup"
    CALCULATION = "calculation"
    RISK = "risk"
    SUMMARY = "summary"
    REVIEW = "review"
    GENERAL = "general"

class IntentResult(BaseModel):
    intent: QueryIntent
    confidence: float
    extracted_entities: dict

def classify_intent(query: str) -> IntentResult:
    """
    Classify the user's query intent using heuristic matching with LLM fallback.
    """
    q_lower = query.lower().strip()

    # Fast heuristic checks for risk, audit, score, and summary
    if any(k in q_lower for k in ("risk factor", "risk score", "confidence score", "confidence and risk", "how risky", "risk rating")):
        return IntentResult(intent=QueryIntent.RISK, confidence=0.95, extracted_entities={})
    
    if any(k in q_lower for k in ("summary", "summarize", "overview of loan", "audit report", "executive summary")):
        return IntentResult(intent=QueryIntent.SUMMARY, confidence=0.90, extracted_entities={})

    if any(k in q_lower for k in ("compare", "comparison", "vs", "difference between")):
        return IntentResult(intent=QueryIntent.COMPARISON, confidence=0.90, extracted_entities={})

    prompt = f"""
Classify the following user question about loans into one of these categories:
- comparison: Comparing two or more loan products (e.g., "Which is cheaper?")
- lookup: Looking up a specific term or value (e.g., "What is the APR?")
- calculation: Needing a numerical calculation (e.g., "What's the total cost?")
- risk: Asking about risk score, risk factors, or document quality/confidence
- summary: Asking for a summary, review, or overview of the loan
- general: General questions that don't fit above

Question: "{query}"

Return ONLY a JSON object with:
{{
  "intent": "comparison|lookup|calculation|risk|summary|general",
  "confidence": 0.0-1.0,
  "extracted_entities": {{"field": "value"}}
}}
"""
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        result = json.loads(content)
        intent_val = result.get("intent", "general")
        if intent_val not in QueryIntent._value2member_map_:
            intent_val = "general"
        return IntentResult(
            intent=QueryIntent(intent_val),
            confidence=float(result.get("confidence", 0.8)),
            extracted_entities=result.get("extracted_entities", {})
        )
    except Exception:
        return IntentResult(
            intent=QueryIntent.GENERAL,
            confidence=0.5,
            extracted_entities={}
        )