"""
Proactive loan document analysis and "Before You Confirm" checklist.

Generates a structured review of extracted facts, missing information,
conflicts, and cost drivers — without requiring a user question.
"""

from typing import List, Dict, Any, Optional, Tuple

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
    Produce the ✓ / ⚠ / ? / 🚨 checklist items with rich actionable metadata and evidence.
    """
    checklist: List[Dict[str, Any]] = []

    def _get_category_and_action(category: str, field: str, value: Any, condition: Optional[str]) -> Tuple[str, str, str, str]:
        cat_lower = category.lower()
        field_lower = field.lower()

        if "interest" in cat_lower or "rate" in cat_lower or "apr" in cat_lower:
            return (
                "Interest & Rates",
                "HIGH",
                f"Verify that {field.replace('_', ' ')} is locked and matches the agreed rate sheet.",
                "Is this rate fixed for the full tenure or linked to an external benchmark spread?",
            )
        elif "processing" in cat_lower or "origination" in cat_lower or "documentation" in cat_lower or "fee" in cat_lower:
            return (
                "Upfront Fees & Deductions",
                "MEDIUM",
                f"Confirm whether {field.replace('_', ' ')} is deducted from loan principal at disbursement.",
                "Will this fee be deducted from the disbursed amount or collected separately?",
            )
        elif "prepay" in cat_lower or "foreclosure" in cat_lower or "early" in cat_lower:
            return (
                "Prepayment & Exit Rules",
                "HIGH",
                "Check for minimum lock-in periods and confirm zero penalty rules for floating rates.",
                "Can I make partial prepayments at any time without advance notice penalties?",
            )
        elif "late" in cat_lower or "penalty" in cat_lower or "default" in cat_lower or "bounce" in cat_lower:
            return (
                "Penalties & Default Terms",
                "HIGH",
                "Verify the exact grace period duration before penal interest or default charges accrue.",
                "What is the exact grace period in days before late charges are applied?",
            )
        elif "tenure" in cat_lower or "repayment" in cat_lower:
            return (
                "Tenure & Repayment",
                "MEDIUM",
                "Verify the total number of installments, EMI amount, and auto-debit dates.",
                "What is the exact monthly EMI due date and auto-debit process?",
            )
        else:
            return (
                "General Conditions",
                "LOW",
                "Review clause terms against lender policy.",
                "Are there any additional conditions attached to this clause?",
            )

    # 1. Add factual items from document
    for fact in facts:
        if fact.category in (
            "interest_rate", "apr", "processing_fee", "other_fee",
            "early_repayment", "prepayment", "late_payment", "default_penalty",
            "fee_waiver", "eligibility", "loan_tenure", "condition", "exception",
        ):
            if fact.status == EvidenceStatus.EXPLICIT:
                marker = "✓"
            elif fact.status in (EvidenceStatus.CONDITIONAL, EvidenceStatus.MIXED):
                marker = "⚠"
            else:
                marker = "?"

            label = fact.field.replace("_", " ").title()
            value_str = f"{fact.value}" if fact.value else "Mentioned in document"
            if fact.unit:
                value_str += f" {fact.unit}"

            group_cat, priority, action, question = _get_category_and_action(
                fact.category, fact.field, fact.value, fact.condition
            )

            checklist.append({
                "item": f"{label}: {value_str}",
                "title": label,
                "value": value_str,
                "category": group_cat,
                "priority": priority,
                "marker": marker,
                "status": fact.status.value,
                "condition": fact.condition,
                "action_guidance": action,
                "suggested_question": question,
                "evidence": {
                    "document": fact.source_document,
                    "page": fact.page,
                    "section": fact.section,
                    "chunk_id": fact.source_chunk_id,
                },
            })

    # 2. Add material omissions / missing fields
    for m in missing:
        field_name = m.get("field", "Item").replace("_", " ").title()
        reason = m.get("reason", "Not specified in document.")
        checklist.append({
            "item": f"{field_name}: Not Documented",
            "title": field_name,
            "value": "Not Specified",
            "category": "Missing Disclosures",
            "priority": "HIGH",
            "marker": "?",
            "status": "NOT_SPECIFIED",
            "condition": reason,
            "action_guidance": f"Request written clarification for {field_name.lower()} before loan confirmation.",
            "suggested_question": f"Can you provide the official schedule and policy for {field_name.lower()} in writing?",
            "evidence": None,
        })

    # 3. Add contractual conflicts
    for c in conflicts:
        field_name = c.get("field", "Contract Clause").replace("_", " ").title()
        desc = c.get("description", "Discrepancy detected across operative documents.")
        checklist.append({
            "item": f"CONFLICT: {field_name}",
            "title": f"Conflict in {field_name}",
            "value": "Contradictory Values",
            "category": "Contract Discrepancies",
            "priority": "HIGH",
            "marker": "🚨",
            "status": "MIXED",
            "condition": desc,
            "action_guidance": "Resolve the discrepancy between the Key Fact Statement and Loan Agreement prior to signing.",
            "suggested_question": f"Which document takes legal precedence regarding {field_name.lower()}?",
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
