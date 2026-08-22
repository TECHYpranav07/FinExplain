"""
LLM generation layer for FinExplain.

Uses Google Gemini LLM API with centralized prompt templates.
Supports both the legacy ``(query, context)`` signature and the new
enriched signature with structured facts, calculations, conflicts, etc.
"""

import json
from app.external.llm_client import llm, client
from app.core.constants import DEFAULT_LLM_MODEL
from app.rag.generation.prompt_templates import (
    SYSTEM_PROMPT_FINANCIAL_EXPERT,
    QA_USER_PROMPT_TEMPLATE,
    LOAN_REVIEW_PROMPT,
    BEFORE_CONFIRMATION_PROMPT,
)
from typing import Dict, Any, List, Optional


def _format_for_prompt(data: Any) -> str:
    """Safely format data for insertion into a prompt template."""
    if data is None:
        return "None"
    if isinstance(data, str):
        return data
    try:
        return json.dumps(data, indent=2, default=str)
    except Exception:
        return str(data)


def generate_answer(
    query: str,
    context: str,
    *,
    structured_facts: Optional[List[Dict[str, Any]]] = None,
    calculation_results: Optional[Dict[str, Any]] = None,
    conflicts: Optional[List[Dict[str, Any]]] = None,
    missing_information: Optional[List[Dict[str, Any]]] = None,
    claim_verification: Optional[Dict[str, Any]] = None,
    evidence_score: Optional[Dict[str, Any]] = None,
    scenario: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate an answer using Groq LLM with evidence-first prompting.

    Backward-compatible: callers passing only ``(query, context)`` still work.
    When the enriched kwargs are provided, uses the full structured QA prompt.
    """
    # Build the user prompt
    prompt = QA_USER_PROMPT_TEMPLATE.format(
        question=query,
        scenario=_format_for_prompt(scenario),
        context=context,
        structured_facts=_format_for_prompt(structured_facts),
        calculation_results=_format_for_prompt(calculation_results),
        conflicts=_format_for_prompt(conflicts),
        missing_information=_format_for_prompt(missing_information),
        claim_verification=_format_for_prompt(claim_verification),
        evidence_score=_format_for_prompt(evidence_score),
    )

    try:
        answer_text = llm.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_FINANCIAL_EXPERT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=2048,
        )

        return {
            "answer": answer_text,
            "raw_response": None,
        }

    except Exception as e:
        return {
            "answer": f"Error generating answer: {str(e)}",
            "error": str(e),
        }


def generate_loan_review(
    structured_facts: List[Dict[str, Any]],
    missing_information: List[Dict[str, Any]],
    conflicts: List[Dict[str, Any]],
    cost_drivers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Generate a proactive loan document review using the LOAN_REVIEW_PROMPT.
    """
    prompt = LOAN_REVIEW_PROMPT.format(
        structured_facts=_format_for_prompt(structured_facts),
        missing_information=_format_for_prompt(missing_information),
        conflicts=_format_for_prompt(conflicts),
        cost_drivers=_format_for_prompt(cost_drivers),
    )

    try:
        content = llm.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_FINANCIAL_EXPERT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        return {"review": content}
    except Exception as e:
        return {"review": f"Error generating review: {str(e)}", "error": str(e)}


def generate_before_confirmation(
    structured_facts: List[Dict[str, Any]],
    missing_information: List[Dict[str, Any]],
    conflicts: List[Dict[str, Any]],
    calculations: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate a "Before You Confirm" checklist.
    """
    prompt = BEFORE_CONFIRMATION_PROMPT.format(
        structured_facts=_format_for_prompt(structured_facts),
        missing_information=_format_for_prompt(missing_information),
        conflicts=_format_for_prompt(conflicts),
        calculations=_format_for_prompt(calculations),
    )

    try:
        content = llm.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_FINANCIAL_EXPERT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        return {"checklist": content}
    except Exception as e:
        return {"checklist": f"Error generating checklist: {str(e)}", "error": str(e)}