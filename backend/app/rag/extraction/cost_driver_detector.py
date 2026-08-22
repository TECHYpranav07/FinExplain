"""
Deterministic cost driver detection.

Filters structured ``LoanFact`` objects for fee/penalty categories and
returns a list of cost driver objects with type, value, condition,
status, and evidence reference.

No LLM calls — pure Python filtering.
"""

from typing import List, Dict, Any

from app.core.loan_categories import LoanFact, EvidenceStatus


# Categories that represent cost drivers
COST_DRIVER_CATEGORIES = {
    "processing_fee",
    "origination_fee",
    "administrative_fee",
    "documentation_fee",
    "other_fee",
    "early_repayment",
    "prepayment",
    "foreclosure",
    "partial_prepayment",
    "late_payment",
    "default_penalty",
    "default_interest",
    "interest_rate",
    "apr",
}


def detect_cost_drivers(facts: List[LoanFact]) -> List[Dict[str, Any]]:
    """
    Filter facts for fee/penalty/rate categories and return structured
    cost driver objects.

    Returns
    -------
    ::

        [
            {
                "type": "processing_fee",
                "value": "2%",
                "condition": None,
                "status": "EXPLICIT",
                "evidence_id": "chunk_182"
            },
            ...
        ]
    """
    drivers: List[Dict[str, Any]] = []

    for fact in facts:
        if fact.category in COST_DRIVER_CATEGORIES:
            drivers.append({
                "type": fact.category,
                "field": fact.field,
                "value": fact.value,
                "unit": fact.unit,
                "currency": fact.currency,
                "condition": fact.condition,
                "status": fact.status.value,
                "evidence_id": fact.source_chunk_id,
                "source_document": fact.source_document,
                "page": fact.page,
            })

    return drivers
