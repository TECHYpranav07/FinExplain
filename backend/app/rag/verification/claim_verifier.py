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
    Use the LLM to break *answer* into discrete factual claims.
    Falls back to sentence-level splitting if the LLM call fails.
    """
    from app.rag.generation.generator import client  # lazy import

    try:
        prompt = CLAIM_EXTRACTION_PROMPT.format(answer=answer)
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": "You decompose text into factual claims. Output only valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=1024,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        claims = json.loads(raw)
        if isinstance(claims, list):
            return claims
    except Exception as e:
        logger.warning(f"[ClaimVerifier] LLM claim extraction failed: {e}")

    # Fallback: sentence splitting
    sentences = re.split(r'(?<=[.!?])\s+', answer)
    return [
        {"claim": s.strip(), "type": "general", "cited_page": None, "cited_document": None}
        for s in sentences
        if s.strip() and len(s.strip()) > 10
    ]


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
        "citation_valid": True,   # innocent until proven invalid
        "condition_preserved": True,
        "issues": [],
    }

    # --- 1 & 2: Citation existence check ---
    if cited_page is not None:
        page_found = any(
            (c.get("page_number") or c.get("page_num")) == cited_page
            for c in chunks
        )
        if not page_found:
            result["citation_valid"] = False
            result["issues"].append(f"Cited page {cited_page} not found in retrieved chunks.")

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

    # --- 4: Value support ---
    best_fact = matching_facts[0]
    result["evidence_id"] = best_fact.source_chunk_id

    value_supported = False
    if best_fact.value:
        value_supported = _value_is_present(best_fact.value, claim_text)
        if not value_supported:
            result["issues"].append(
                f"Claim value does not match the supported value '{best_fact.value}'."
            )
    else:
        # An unquantified source fact can support a general statement about
        # the term, but cannot support a claim that introduces a value.
        value_supported = claim.get("type") not in ("value", "comparison")

    if value_supported and best_fact.status in (EvidenceStatus.EXPLICIT, EvidenceStatus.CONDITIONAL):
        result["supported"] = True
        result["status"] = best_fact.status.value

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
    """Match numeric values without accepting a different number as support."""
    normalized_value = value.lower().replace(",", "").strip()
    normalized_claim = claim.lower().replace(",", "")

    if not re.search(r"\d", normalized_value) and re.search(
        rf"(?<!\w){re.escape(normalized_value)}(?!\w)", normalized_claim
    ):
        return True

    # Treat equivalent numeric spellings such as ``2`` and ``2.0`` as equal,
    # while avoiding substring matches such as ``2`` inside ``12``. Compound
    # values (for example ``500 + 2%``) require every numeric component.
    value_numbers = re.findall(r"(?<!\d)[-+]?\d+(?:\.\d+)?(?!\d)", normalized_value)
    if not value_numbers:
        return False

    claim_numbers = re.findall(
        r"(?<!\d)[-+]?\d+(?:\.\d+)?(?!\d)", normalized_claim
    )
    try:
        claim_numeric_values = [float(number) for number in claim_numbers]
        return all(
            float(number) in claim_numeric_values for number in value_numbers
        )
    except ValueError:
        return False
