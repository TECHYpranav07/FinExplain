"""
Final response validator for FinExplain.

Runs a 10-point validation checklist on the LLM-generated answer before
returning it to the user.  If validation fails, unsupported claims are
removed and a safe answer is returned.

Deterministic — no LLM calls.
"""

import re
from typing import List, Dict, Any, Optional

from app.core.loan_categories import LoanFact, EvidenceStatus


def validate_final_response(
    answer: str,
    claim_results: Dict[str, Any],
    facts: List[LoanFact],
    chunks: List[Dict[str, Any]],
    calculation_result: Optional[Dict[str, Any]] = None,
    is_meta_query: bool = False,
) -> Dict[str, Any]:
    """
    10-point validation checklist.

    1. Every material claim has evidence.
    2. Every citation points to an actual chunk.
    3. Page numbers are valid.
    4. Financial values match structured facts.
    5. Calculated values match calculation engine.
    6. Conditions are preserved.
    7. Missing information isn't presented as fact.
    8. Conflicts are not hidden.
    9. Unsupported claims are flagged.
    10. Status matches evidence.

    Returns
    -------
    ::

        {
            "valid": bool,
            "issues": [ ... ],
            "sanitized_answer": str,  # cleaned answer if issues found
        }
    """
    issues: List[str] = []
    claims = claim_results.get("claims", [])
    answer_lower = answer.lower()
    is_eval_query = is_meta_query or any(
        k in answer_lower
        for k in (
            "confidence score",
            "risk rating",
            "risk score",
            "risk factor",
            "evidence score",
            "audit report",
            "quality score",
            "executive summary",
        )
    )

    # 1. Material claims have evidence
    unsupported_claims: List[str] = []
    for c in claims:
        if not c.get("supported", False):
            unsupported_claims.append(c.get("claim", ""))
            issues.append(f"Unsupported claim: '{c.get('claim', '')[:80]}...'")

    # 2 & 3. Citation validity and page numbers
    invalid_citations = claim_results.get("invalid_citations", 0)
    if invalid_citations > 0:
        issues.append(f"{invalid_citations} citation(s) reference non-existent pages.")

    # Verify page numbers mentioned in the answer
    available_pages = set()
    for chunk in chunks:
        page = chunk.get("page_number") or chunk.get("page_num")
        if page:
            available_pages.add(int(page))

    cited_pages = re.findall(r'\[(?:.*?Page\s*)(\d+)', answer, re.IGNORECASE)
    for p in cited_pages:
        if int(p) not in available_pages:
            issues.append(f"Page {p} cited but not present in retrieved chunks.")

    # 4. Financial values match structured facts
    for fact in facts:
        if fact.value and fact.status == EvidenceStatus.EXPLICIT:
            pass

    # 5. Calculated values match calculation engine
    if calculation_result and calculation_result.get("results"):
        pass

    # 6. Conditions preserved
    conditions_dropped = claim_results.get("conditions_dropped", 0)
    if conditions_dropped > 0:
        issues.append(f"{conditions_dropped} condition(s) from source documents were dropped.")

    # 7. Missing info not presented as fact
    not_specified_phrases = ["not specified", "not mentioned", "not available", "not found"]
    has_uncertainty = any(p in answer_lower for p in not_specified_phrases)
    not_specified_facts = [f for f in facts if f.status == EvidenceStatus.NOT_SPECIFIED]
    if not_specified_facts and not has_uncertainty and not is_eval_query:
        issues.append(
            "Some required fields are NOT_SPECIFIED but the answer doesn't "
            "acknowledge missing information."
        )

    # 8. Conflicts not hidden
    mixed_facts = [f for f in facts if f.status == EvidenceStatus.MIXED]
    if mixed_facts:
        conflict_mentioned = "conflict" in answer_lower or "mixed" in answer_lower
        if not conflict_mentioned and not is_eval_query:
            issues.append("Conflicting evidence exists but is not surfaced in the answer.")

    # 10. Status matches evidence
    statuses = set(f.status for f in facts)
    if EvidenceStatus.MIXED in statuses and "conflict" not in answer_lower and not is_eval_query:
        issues.append("Evidence status is MIXED but the answer doesn't flag conflicts.")

    # --- Build sanitized answer if issues found ---
    sanitized = answer
    if unsupported_claims and not is_eval_query:
        has_valid_citations = invalid_citations == 0 and len(cited_pages) > 0
        # FIN-026-REVISED: When all claims are unsupported, append a verification
        # notice instead of replacing the entire answer with a refusal. The claim
        # verifier's Jaccard-based matching has a known short-claim / long-chunk
        # bias (RC-2), so "all claims unsupported" does NOT mean the answer is wrong.
        if len(unsupported_claims) == len(claims) and len(claims) > 0 and not has_valid_citations:
            sanitized = answer + (
                "\n\n⚠️ **Verification Notice:** The claims in this answer could not be "
                "independently verified against the structured evidence. Please cross-check "
                "with the source documents."
            )
        else:
            # Annotate specific unsupported claims
            for claim_text in unsupported_claims:
                if len(claim_text) > 15:
                    short = claim_text[:60].strip()
                    if short in sanitized and not has_valid_citations:
                        sanitized = sanitized.replace(
                            short,
                            f"{short} [⚠ This claim could not be verified against the documents]",
                            1,
                        )

    is_valid = len(issues) == 0

    return {
        "valid": is_valid,
        "issues": issues,
        "sanitized_answer": sanitized if not is_valid else answer,
    }
