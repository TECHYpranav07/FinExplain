"""
Claim-level evidence verification.

Breaks the LLM-generated answer into individual factual claims, then
verifies each claim independently against the structured ``LoanFact``
objects and retrieved chunks.

This prevents one valid citation from making the entire answer appear
trustworthy when other claims are unsupported.
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional

from app.core.loan_categories import LoanFact, EvidenceStatus
from app.rag.extraction.condition_detector import detect_conditions

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Claim extraction (LLM-assisted)
# ---------------------------------------------------------------------------

CLAIM_EXTRACTION_PROMPT = """Break the following answer into individual factual claims.

A "claim" is any statement that asserts a financial fact, value, condition,
fee, rate, penalty, eligibility rule, date, or comparison conclusion.

Return a JSON array of objects:
[
  {{
    "claim": "<the factual statement>",
    "type": "value | condition | comparison | general",
    "cited_page": <page number if cited, else null>,
    "cited_document": "<document name if cited, else null>"
  }}
]

Ignore headings, structural labels, and pure explanations that do not assert
a financial fact.

Answer to decompose:
{answer}

Return ONLY the JSON array.
"""


def extract_claims(answer: str) -> List[Dict[str, Any]]:
    """
    Deterministically break answer into discrete factual claims using sentence
    and citation parsing, eliminating unnecessary LLM token consumption and latency.
    """
    sentences = re.split(r'(?<=[.!?\n])\s+', answer.strip())
    claims: List[Dict[str, Any]] = []
    for s in sentences:
        s_clean = s.strip()
        if not s_clean or len(s_clean) < 10:
            continue
        # Extract cited page if present (e.g. [Page 1, Section 2])
        page_match = re.search(r'\[(?:.*?Page\s*)(\d+)', s_clean, re.IGNORECASE)
        cited_page = int(page_match.group(1)) if page_match else None

        # Extract cited doc if present
        doc_match = re.search(r'\[([^,\]]+)(?:,\s*Page|\s*Page)', s_clean, re.IGNORECASE)
        cited_doc = doc_match.group(1).strip() if doc_match else None

        claims.append({
            "claim": s_clean,
            "type": "value" if re.search(r'\d', s_clean) else "general",
            "cited_page": cited_page,
            "cited_document": cited_doc,
        })
    return claims


# ---------------------------------------------------------------------------
# Deterministic single-claim verification
# ---------------------------------------------------------------------------

def verify_claim(
    claim: Dict[str, Any],
    facts: List[LoanFact],
    chunks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Deterministically verify a single claim against evidence.

    Checks
    ------
    1. Does the cited chunk actually exist?
    2. Does the cited page exist in retrieved chunks?
    3. Does the evidence contain information related to the claim?
    4. Does the evidence support the exact value stated?
    5. Does the evidence contain conditions that the claim omitted?
    6. Is the claim contradicted by another retrieved source?

    Returns
    -------
    ::

        {
            "claim": "...",
            "supported": bool,
            "evidence_id": "chunk_xxx" | None,
            "status": "EXPLICIT" | "CONDITIONAL" | "MIXED" | "NOT_SPECIFIED",
            "citation_valid": bool,
            "condition_preserved": bool,
            "issues": [ ... ],
        }
    """
    claim_text = claim.get("claim", "")
    cited_page = claim.get("cited_page")
    cited_doc = claim.get("cited_document")

    result: Dict[str, Any] = {
        "claim": claim_text,
        "supported": False,
        "evidence_id": None,
        "status": "NOT_SPECIFIED",
        "citation_valid": False,   # FIN-007: guilty until proven valid (was True)
        "condition_preserved": True,
        "issues": [],
    }

    # --- 1 & 2: Citation existence check ---
    if cited_page is not None:
        page_found = any(
            (c.get("page_number") or c.get("page_num")) == cited_page
            for c in chunks
        )
        if page_found:
            result["citation_valid"] = True  # Confirmed: page exists
        else:
            result["issues"].append(f"Cited page {cited_page} not found in retrieved chunks.")
    elif not cited_page:
        # No page cited at all — can't verify
        result["issues"].append("No page citation provided for this claim.")

    # --- 3: Evidence relevance — check if any fact relates to the claim ---
    claim_lower = claim_text.lower()
    matching_facts: List[LoanFact] = []
    for fact in facts:
        # Simple keyword overlap check
        field_lower = fact.field.lower().replace("_", " ")
        category_lower = fact.category.lower().replace("_", " ")
        source_lower = (fact.source_text or "").lower()

        if (
            field_lower in claim_lower
            or category_lower in claim_lower
            or (fact.value and fact.value.lower() in claim_lower)
            or (source_lower and _text_overlap(claim_lower, source_lower) > 0.3)
        ):
            matching_facts.append(fact)

    if not matching_facts:
        # No related evidence found
        result["status"] = "NOT_SPECIFIED"
        result["issues"].append("No matching structured fact found for this claim.")
        return result

    # --- 4: Value support — check all candidate matching facts ---
    value_supported = False
    best_fact = None
    for fact in matching_facts:
        if fact.value:
            if _value_is_present(fact.value, claim_text):
                value_supported = True
                best_fact = fact
                break
        else:
            if claim.get("type") not in ("value", "comparison"):
                value_supported = True
                best_fact = fact
                break

    if not best_fact:
        best_fact = matching_facts[0]
        if best_fact.value and not value_supported:
            result["issues"].append(
                f"Claim value does not match the supported value '{best_fact.value}'."
            )

    result["evidence_id"] = best_fact.source_chunk_id

    # Fallback to direct chunk text overlap ONLY when numbers match or for general claims
    if not value_supported:
        claim_numbers = re.findall(r"(?<!\d)[-+]?\d+(?:\.\d+)?(?!\d)", claim_lower)
        for chunk in chunks:
            chunk_text = (chunk.get("text") or chunk.get("content") or "").lower()
            if claim_numbers:
                chunk_numbers = re.findall(r"(?<!\d)[-+]?\d+(?:\.\d+)?(?!\d)", chunk_text)
                try:
                    c_floats = [float(n) for n in claim_numbers]
                    ch_floats = [float(n) for n in chunk_numbers]
                    if all(n in ch_floats for n in c_floats) and _text_overlap(claim_lower, chunk_text) > 0.25:
                        value_supported = True
                        result["evidence_id"] = chunk.get("id") or chunk.get("chunk_id")
                        break
                except ValueError:
                    pass
            else:
                if _text_overlap(claim_lower, chunk_text) > 0.35:
                    value_supported = True
                    result["evidence_id"] = chunk.get("id") or chunk.get("chunk_id")
                    break

    if value_supported:
        result["supported"] = True
        if best_fact and hasattr(best_fact, "status"):
            result["status"] = getattr(best_fact.status, "value", str(best_fact.status))
        else:
            result["status"] = "EXPLICIT"

    # --- 5: Condition preservation ---
    if best_fact.condition:
        condition_lower = best_fact.condition.lower()
        # Check if the claim mentions the condition
        if condition_lower not in claim_lower:
            # Check for key condition words
            key_words = [w for w in condition_lower.split() if len(w) > 3]
            preserved = any(w in claim_lower for w in key_words) if key_words else True
            if not preserved:
                result["condition_preserved"] = False
                result["issues"].append(
                    f"Condition '{best_fact.condition}' not preserved in claim."
                )

    # --- 6: Contradiction check ---
    if len(matching_facts) > 1:
        values = set(f.value for f in matching_facts if f.value)
        if len(values) > 1:
            result["status"] = "MIXED"
            result["issues"].append(
                f"Multiple conflicting values found: {', '.join(values)}"
            )

    # Check source text conditions the claim may have dropped
    source_conditions = detect_conditions(best_fact.source_text or "")
    claim_conditions = detect_conditions(claim_text)
    if source_conditions and not claim_conditions:
        result["condition_preserved"] = False
        result["issues"].append(
            "Source text contains conditional language not reflected in the claim."
        )

    return result


# ---------------------------------------------------------------------------
# Orchestrator: verify all claims
# ---------------------------------------------------------------------------

def verify_all_claims(
    answer: str,
    facts: List[LoanFact],
    chunks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Extract claims from *answer*, verify each independently, and return
    aggregate results.

    Returns
    -------
    ::

        {
            "claims": [ ... ],          # per-claim verification results
            "total_claims": int,
            "supported_claims": int,
            "unsupported_claims": int,
            "invalid_citations": int,
            "conditions_dropped": int,
            "claim_coverage": float,    # supported / total
        }
    """
    raw_claims = extract_claims(answer)

    results: List[Dict[str, Any]] = []
    supported = 0
    unsupported = 0
    invalid_citations = 0
    conditions_dropped = 0

    for raw_claim in raw_claims:
        verification = verify_claim(raw_claim, facts, chunks)
        results.append(verification)

        if verification["supported"]:
            supported += 1
        else:
            unsupported += 1
        if not verification["citation_valid"]:
            invalid_citations += 1
        if not verification["condition_preserved"]:
            conditions_dropped += 1

    total = len(results) or 1

    return {
        "claims": results,
        "total_claims": len(results),
        "supported_claims": supported,
        "unsupported_claims": unsupported,
        "invalid_citations": invalid_citations,
        "conditions_dropped": conditions_dropped,
        "claim_coverage": round(supported / total, 3),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text_overlap(a: str, b: str) -> float:
    """Simple word-level Jaccard overlap between two strings."""
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def _value_is_present(value: str, claim: str) -> bool:
    """Match numeric values accurately without false rejection or substring leaks."""
    normalized_value = value.lower().replace(",", "").strip()
    normalized_claim = claim.lower().replace(",", "")

    # Non-numeric direct word-boundary match
    if not re.search(r"\d", normalized_value):
        return bool(re.search(rf"(?<!\w){re.escape(normalized_value)}(?!\w)", normalized_claim))

    value_numbers = re.findall(r"(?<!\d)[-+]?\d+(?:\.\d+)?(?!\d)", normalized_value)
    if not value_numbers:
        return True

    claim_numbers = re.findall(r"(?<!\d)[-+]?\d+(?:\.\d+)?(?!\d)", normalized_claim)
    if not claim_numbers:
        return False

    try:
        claim_numeric_values = [float(number) for number in claim_numbers]
        value_numeric_values = [float(number) for number in value_numbers]
        return any(v in claim_numeric_values for v in value_numeric_values)
    except ValueError:
        return False
