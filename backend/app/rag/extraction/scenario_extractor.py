"""
Scenario extraction from user queries.

Uses the LLM to extract structured financial scenario parameters
(principal, currency, tenure, etc.) from a natural-language question.

Does NOT assume anything not explicitly stated by the user.
"""

import json
import logging
from typing import Dict, Any, Optional

from app.rag.generation.generator import client

logger = logging.getLogger(__name__)

SCENARIO_EXTRACTION_PROMPT = """Extract the financial scenario from the user's question.

Return a JSON object with ONLY the fields mentioned by the user.
Do NOT assume or invent any values not explicitly stated.

Possible fields:
- "principal": number (loan amount)
- "currency": string (INR, USD, EUR, etc.)
- "repayment_period": number
- "repayment_unit": string (months, years, days)
- "interest_rate": number (if user specifies)
- "repayment_type": string (emi, bullet, lump_sum, etc.)

If the user does not mention a field, do NOT include it.
Do NOT assume "monthly EMI" unless explicitly stated.

User question:
"{query}"

Return ONLY the JSON object — no commentary.
"""


def extract_user_scenario(query: str) -> Dict[str, Any]:
    """
    Extract structured scenario parameters from a user query.

    Examples
    --------
    "I need ₹10 lakh and will repay it in 6 months."
    → {"principal": 1000000, "currency": "INR", "repayment_period": 6, "repayment_unit": "months"}

    Returns an empty dict if nothing can be extracted.
    """
    prompt = SCENARIO_EXTRACTION_PROMPT.format(query=query)

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": "You extract structured financial scenarios. Output only valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=256,
        )
        raw = response.choices[0].message.content.strip()

        # Handle markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        scenario = json.loads(raw)
        return scenario if isinstance(scenario, dict) else {}

    except Exception as e:
        logger.warning(f"[ScenarioExtractor] Extraction failed: {e}")
        return {}
