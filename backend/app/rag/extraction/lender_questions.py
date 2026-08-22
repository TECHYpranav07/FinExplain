"""
Dynamic Lender Questions Generator.

Generates questions to ask the loan provider based ONLY on detected
document gaps, conditions, conflicts, missing amounts, or scenario-specific risks.

Does NOT generate generic spam questions.
"""

from typing import List, Dict, Any, Optional
from app.core.loan_categories import LoanFact, EvidenceStatus

def generate_lender_questions(
    facts: List[LoanFact],
    missing: List[Dict[str, Any]],
    conflicts: List[Dict[str, Any]],
    risk_factors: Optional[List[Dict[str, Any]]] = None,
    scenario: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Generate tailored, actionable questions to ask the loan provider.
    """
    questions: List[str] = []
    seen_topics = set()

    # 1. From Document Conflicts
    for conf in conflicts:
        field = conf.get("field", "loan terms").replace("_", " ")
        q = f"Which document version or clause governs the {field}, as conflicting terms were found?"
        if q not in questions:
            questions.append(q)

    # 2. From Scenario-Specific Risks
    scenario = scenario or {}
    user_tenure = scenario.get("repayment_period")
    for fact in facts:
        if fact.category in ("early_repayment", "prepayment") and fact.condition:
            if user_tenure:
                q = f"How much will I be charged if I repay the loan after {user_tenure} months, given that prepayment rules state: '{fact.condition}'?"
            else:
                q = f"Does the prepayment fee waiver '{fact.condition}' apply to my specific planned repayment schedule?"
            if "prepayment" not in seen_topics:
                questions.append(q)
                seen_topics.add("prepayment")

    # 3. From Conditional Terms / Waivers
    for fact in facts:
        if fact.status == EvidenceStatus.CONDITIONAL and fact.condition and fact.category not in ("early_repayment", "prepayment"):
            field = fact.field.replace("_", " ")
            q = f"What specific documentation or criteria are needed to satisfy the condition for {field} ('{fact.condition}')?"
            if field not in seen_topics:
                questions.append(q)
                seen_topics.add(field)

    # 4. From Unspecified Penalty / Fee Amounts
    for fact in facts:
        if fact.category in ("late_payment", "default_penalty", "other_fee") and (not fact.value or fact.value.lower() in ("null", "none", "unknown")):
            field = fact.field.replace("_", " ")
            q = f"What exact monetary fee or interest surcharge applies to {field}?"
            if field not in seen_topics:
                questions.append(q)
                seen_topics.add(field)

    # 5. From Missing Information
    for item in missing:
        f = item.get("field", "")
        if f == "apr" and "apr" not in seen_topics:
            questions.append("What is the official Annual Percentage Rate (APR) inclusive of all mandatory upfront charges?")
            seen_topics.add("apr")
        elif f == "processing_fee" and "processing_fee" not in seen_topics:
            questions.append("What is the exact processing/origination fee, and is it non-refundable?")
            seen_topics.add("processing_fee")
        elif f == "late_payment" and "late_payment" not in seen_topics:
            questions.append("What exact grace period and penalty rate applies if a scheduled payment is delayed?")
            seen_topics.add("late_payment")
        elif f == "early_repayment" and "prepayment" not in seen_topics:
            questions.append("Are there any foreclosure or prepayment charges if I choose to settle the loan early?")
            seen_topics.add("prepayment")

    # Limit to top 5 most critical questions to avoid overwhelming the borrower
    return questions[:5]
