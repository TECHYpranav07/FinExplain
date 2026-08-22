"""
Loan product comparison engine for FinExplain.

Two complementary comparators:
1. ``compare_loan_products()`` — original metadata-level comparison
   (backward-compatible).
2. ``compare_loan_facts()`` — new structured-fact-level comparison
   across APR + interest + fees + early repayment + late payment +
   waivers + conditions.  Deterministic — does NOT ask the LLM
   "which is cheaper?".
"""

from typing import List, Dict, Any, Optional

from app.core.loan_categories import LoanFact, EvidenceStatus, REQUIRED_COMPARISON_FIELDS


# ---------------------------------------------------------------------------
# 1. Original metadata-level comparison (backward compatible)
# ---------------------------------------------------------------------------

def compare_loan_products(
    product_a: Dict[str, Any],
    product_b: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compare two loan products side by side.
    """
    return {
        "product_a": {
            "name": product_a.get("name"),
            "issuer": product_a.get("issuer"),
            "effective_date": product_a.get("effective_date"),
        },
        "product_b": {
            "name": product_b.get("name"),
            "issuer": product_b.get("issuer"),
            "effective_date": product_b.get("effective_date"),
        },
        "comparison_points": [
            {
                "attribute": "Issuer",
                "val_a": product_a.get("issuer"),
                "val_b": product_b.get("issuer"),
            },
            {
                "attribute": "Effective Date",
                "val_a": product_a.get("effective_date"),
                "val_b": product_b.get("effective_date"),
            },
        ],
    }


# ---------------------------------------------------------------------------
# 2. New structured-fact-level comparison
# ---------------------------------------------------------------------------

def compare_loan_facts(
    product_a_facts: List[LoanFact],
    product_b_facts: List[LoanFact],
    scenario: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Field-by-field comparison using structured facts.

    Compares APR + interest + upfront fees + recurring fees + early
    repayment + late payment + waivers + conditions.

    Deterministic cost comparison — does NOT ask the LLM "which is cheaper?".
    The LLM should explain the comparison result and its limitations.

    Returns
    -------
    ::

        {
            "field_comparison": [ ... ],
            "known_cost_a": float | None,
            "known_cost_b": float | None,
            "missing_fields_a": [ ... ],
            "missing_fields_b": [ ... ],
            "conflicts": [ ... ],
            "comparison_complete": bool,
            "comparison_summary": str,
        }
    """

    def _build_fact_map(facts: List[LoanFact]) -> Dict[str, List[LoanFact]]:
        """Group facts by field."""
        m: Dict[str, List[LoanFact]] = {}
        for f in facts:
            m.setdefault(f.field, []).append(f)
            m.setdefault(f.category, []).append(f)
        return m

    map_a = _build_fact_map(product_a_facts)
    map_b = _build_fact_map(product_b_facts)

    # All fields to compare
    all_fields = set(REQUIRED_COMPARISON_FIELDS)
    all_fields.update(map_a.keys())
    all_fields.update(map_b.keys())

    field_comparison: List[Dict[str, Any]] = []
    missing_a: List[str] = []
    missing_b: List[str] = []
    conflicts: List[Dict[str, Any]] = []

    for field in sorted(all_fields):
        facts_a = map_a.get(field, [])
        facts_b = map_b.get(field, [])

        entry: Dict[str, Any] = {
            "field": field,
            "product_a": None,
            "product_b": None,
            "status_a": "NOT_SPECIFIED",
            "status_b": "NOT_SPECIFIED",
            "winner": None,
        }

        if facts_a:
            best_a = facts_a[0]
            entry["product_a"] = {
                "value": best_a.value,
                "unit": best_a.unit,
                "condition": best_a.condition,
            }
            entry["status_a"] = best_a.status.value
        else:
            if field in REQUIRED_COMPARISON_FIELDS:
                missing_a.append(field)

        if facts_b:
            best_b = facts_b[0]
            entry["product_b"] = {
                "value": best_b.value,
                "unit": best_b.unit,
                "condition": best_b.condition,
            }
            entry["status_b"] = best_b.status.value
        else:
            if field in REQUIRED_COMPARISON_FIELDS:
                missing_b.append(field)

        # Deterministic comparison for numeric fields
        if entry["product_a"] and entry["product_b"]:
            try:
                val_a = float(
                    str(entry["product_a"]["value"]).replace("%", "").replace(",", "").strip()
                )
                val_b = float(
                    str(entry["product_b"]["value"]).replace("%", "").replace(",", "").strip()
                )
                if val_a < val_b:
                    entry["winner"] = "product_a"
                elif val_b < val_a:
                    entry["winner"] = "product_b"
                else:
                    entry["winner"] = "equal"
            except (ValueError, TypeError):
                entry["winner"] = "non_numeric"

        field_comparison.append(entry)

    # Determine if comparison is complete
    comparison_complete = len(missing_a) == 0 and len(missing_b) == 0

    # Build summary
    if comparison_complete:
        summary = "All required comparison fields are available for both products."
    else:
        summary = (
            f"Comparison is incomplete. "
            f"Product A is missing: {', '.join(missing_a) or 'none'}. "
            f"Product B is missing: {', '.join(missing_b) or 'none'}."
        )

    return {
        "field_comparison": field_comparison,
        "missing_fields_a": missing_a,
        "missing_fields_b": missing_b,
        "conflicts": conflicts,
        "comparison_complete": comparison_complete,
        "comparison_summary": summary,
    }
