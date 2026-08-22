"""
Proactive loan document analysis and "Before You Confirm" checklist.

Generates a structured review of extracted facts, missing information,
conflicts, and cost drivers — without requiring a user question.
"""

from typing import List, Dict, Any, Optional

from app.core.loan_categories import LoanFact, EvidenceStatus


def analyze_loan_document(
    facts: List[LoanFact],
    missing: List[Dict[str, Any]],
    conflicts: List[Dict[str, Any]],
    cost_drivers: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Generate a structured proactive loan review from extracted data.

    Returns a dict with sections:
    loan_summary, cost_drivers, repayment_conditions, penalty_risks,
    eligibility, waivers, exceptions, missing_information, conflicts,
    important_dates.
    """
    cost_drivers = cost_drivers or []

    # Categorise facts
    def _facts_by_category(*categories: str) -> List[Dict[str, Any]]:
        return [
            f.model_dump() for f in facts if f.category in categories
        ]

    review: Dict[str, Any] = {
        "loan_summary": {
            "total_facts_extracted": len(facts),
            "total_missing_fields": len(missing),
            "total_conflicts": len(conflicts),
            "rates": _facts_by_category("interest_rate", "apr"),
            "amounts": _facts_by_category("loan_amount"),
        },
        "cost_drivers": cost_drivers,
        "repayment_conditions": _facts_by_category(
            "repayment_schedule", "loan_tenure", "grace_period"
        ),
        "penalty_risks": _facts_by_category(
            "late_payment", "default_penalty", "default_interest"
        ),
        "early_repayment": _facts_by_category(
            "early_repayment", "prepayment", "foreclosure", "partial_prepayment"
        ),
        "eligibility": _facts_by_category(
            "eligibility",
            "income_requirement",
            "credit_requirement",
            "employment_requirement",
            "residency_requirement",
        ),
        "waivers": _facts_by_category("fee_waiver"),
        "exceptions": _facts_by_category("exclusion", "exception"),
        "conditions": _facts_by_category("condition"),
        "important_dates": _facts_by_category(
            "effective_date", "expiry_date", "document_version"
        ),
        "missing_information": missing,
        "conflicts": conflicts,
    }

    return review


def generate_before_confirmation_checklist(
    facts: List[LoanFact],
    missing: List[Dict[str, Any]],
    conflicts: List[Dict[str, Any]],
    calculations: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Produce the ✓ / ⚠ / ? checklist items with evidence attached.

    Returns a list of checklist items::

        [
            {
                "item": "APR: 10.5%",
                "marker": "✓",
                "status": "EXPLICIT",
                "evidence": { ... },
            },
            ...
        ]
    """
    checklist: List[Dict[str, Any]] = []

    for fact in facts:
        if fact.category in (
            "interest_rate", "apr", "processing_fee", "other_fee",
            "early_repayment", "prepayment", "late_payment", "default_penalty",
            "fee_waiver", "eligibility", "loan_tenure",
        ):
            if fact.status == EvidenceStatus.EXPLICIT:
                marker = "✓"
            elif fact.status == EvidenceStatus.CONDITIONAL:
                marker = "⚠"
            elif fact.status == EvidenceStatus.MIXED:
                marker = "⚠"
            else:
                marker = "?"

            label = fact.field.replace("_", " ").title()
            value_str = f"{fact.value}" if fact.value else "see document"
            if fact.unit:
                value_str += f" {fact.unit}"

            checklist.append({
                "item": f"{label}: {value_str}",
                "marker": marker,
                "status": fact.status.value,
                "condition": fact.condition,
                "evidence": {
                    "document": fact.source_document,
                    "page": fact.page,
                    "section": fact.section,
                    "chunk_id": fact.source_chunk_id,
                },
            })

    # Add missing fields
    for m in missing:
        checklist.append({
            "item": m["field"].replace("_", " ").title(),
            "marker": "?",
            "status": "NOT_SPECIFIED",
            "condition": None,
            "evidence": None,
        })

    # Add conflicts
    for c in conflicts:
        checklist.append({
            "item": f"{c.get('field', 'Unknown')}: conflict detected",
            "marker": "⚠",
            "status": "MIXED",
            "condition": None,
            "evidence": c.get("values"),
        })

    return checklist


def prioritize_cost_drivers(
    facts: List[LoanFact],
    scenario: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Rank findings by financial impact using deterministic rules.

    Priority levels:
    - HIGH: penalties, early repayment fees, conditional charges
    - MEDIUM: processing fees, fixed fees, recurring charges
    - LOW: administrative info, general conditions
    """
    cost_categories_high = {
        "early_repayment", "prepayment", "foreclosure", "late_payment",
        "default_penalty", "default_interest",
    }
    cost_categories_medium = {
        "processing_fee", "origination_fee", "administrative_fee",
        "documentation_fee", "other_fee", "fee_waiver",
    }

    prioritized: List[Dict[str, Any]] = []

    for fact in facts:
        if fact.category in cost_categories_high:
            priority = "HIGH"
        elif fact.category in cost_categories_medium:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        # Boost priority if the fact is conditional (more risk)
        if fact.status == EvidenceStatus.CONDITIONAL and priority == "MEDIUM":
            priority = "HIGH"

        prioritized.append({
            "priority": priority,
            "category": fact.category,
            "field": fact.field,
            "value": fact.value,
            "condition": fact.condition,
            "status": fact.status.value,
            "evidence_id": fact.source_chunk_id,
        })

    # Sort by priority (HIGH first)
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    prioritized.sort(key=lambda x: priority_order.get(x["priority"], 3))

    return prioritized
