"""
Deterministic missing-information detection.

Compares extracted ``LoanFact`` categories against a required-field checklist
and reports which fields were not found in the evidence.

No LLM calls — pure Python set comparison.
"""

from typing import List, Dict, Any

from app.core.loan_categories import (
    LoanFact,
    EvidenceStatus,
    REQUIRED_COMPARISON_FIELDS,
    normalize_field_name,
)


def detect_missing_information(
    facts: List[LoanFact],
    required_fields: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """
    Compare the categories / fields present in *facts* against
    *required_fields* (defaults to ``REQUIRED_COMPARISON_FIELDS``).

    Returns a list of missing-field reports::

        [
            {
                "field": "apr",
                "status": "NOT_SPECIFIED",
                "reason": "No supporting clause found in provided documents."
            },
            ...
        ]
    """
    if required_fields is None:
        required_fields = list(REQUIRED_COMPARISON_FIELDS)

    # Collect all categories and fields that have actual evidence
    found_categories: set[str] = set()
    found_fields: set[str] = set()
    for fact in facts:
        if fact.status != EvidenceStatus.NOT_SPECIFIED:
            found_categories.add(normalize_field_name(fact.category))
            found_fields.add(normalize_field_name(fact.field))

    missing: List[Dict[str, Any]] = []
    for field in required_fields:
        if field not in found_categories and field not in found_fields:
            missing.append({
                "field": field,
                "status": "NOT_SPECIFIED",
                "reason": "No supporting clause found in provided documents.",
            })

    return missing
