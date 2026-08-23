"""
Deterministic query router for FinExplain.

Classifies user queries into processing tiers that control which pipeline
stages are executed.  This is the most impactful latency optimization —
simple factual queries no longer run through the full 21-stage pipeline.

Tiers
-----
FAST_FACTUAL    "What is the interest rate?"  → Structured fact DB lookup, no reranker, no fact LLM
STANDARD_RAG    "What if I default?"          → Hybrid retrieval + RRF, conditional reranker
DEEP_RAG        "Review all risks"            → Full pipeline (reranker + fact LLM + risk engine)
CALCULATION     "How much EMI for 5 years?"   → Structured facts + deterministic calculator + LLM explanation
"""

import re
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class QueryTier(str, Enum):
    FAST_FACTUAL = "fast_factual"
    STANDARD_RAG = "standard_rag"
    DEEP_RAG = "deep_rag"
    CALCULATION = "calculation"


# ---------------------------------------------------------------------------
# Known financial field patterns that can be answered from structured facts
# ---------------------------------------------------------------------------
_FACTUAL_FIELD_PATTERNS = [
    (re.compile(r"\b(?:penal(?:ty)?\s*(?:interest|rate|charge)|late\s*(?:payment\s*)?(?:fee|charge|penalty))\b", re.I), "penal_interest"),
    (re.compile(r"\b(?:prepayment|foreclosure|early\s*(?:closure|repayment|settlement))\s*(?:fee|charge|penalty)?\b", re.I), "prepayment_fee"),
    (re.compile(r"\b(?:processing\s*(?:fee|charge)|admin(?:istrative)?\s*(?:fee|charge)|origination\s*fee|upfront\s*fee)\b", re.I), "processing_fee"),
    (re.compile(r"\b(?:documentation\s*(?:fee|charge)|doc\s*fee|stamp\s*duty)\b", re.I), "documentation_fee"),
    (re.compile(r"\b(?:bounce\s*charge|ecs\s*bounce|cheque\s*bounce|nach\s*bounce)\b", re.I), "bounce_charge"),
    (re.compile(r"\b(?:cooling[\s-]off\s*period)\b", re.I), "cooling_off_period"),
    (re.compile(r"\b(?:grace\s*period|moratorium)\b", re.I), "grace_period"),
    (re.compile(r"\b(?:apr|annual\s*percentage\s*rate|effective\s*(?:annual\s*)?rate)\b", re.I), "apr"),
    (re.compile(r"\b(?:monthly\s*emi|emi\s*amount|installment|instalment)\b", re.I), "emi"),
    (re.compile(r"\b(?:interest\s*rate|rate\s*of\s*interest|roi|annual\s*rate)\b", re.I), "interest_rate"),
    (re.compile(r"\b(?:tenure|loan\s*(?:duration|period|term)|repayment\s*period)\b", re.I), "tenure"),
    (re.compile(r"\b(?:loan\s*amount|principal|sanction(?:ed)?\s*amount|disburs(?:ed|ement)\s*amount)\b", re.I), "loan_amount"),
    (re.compile(r"\b(?:insurance|credit\s*life|loan\s*protection)\b", re.I), "insurance"),
    (re.compile(r"\b(?:collateral|security|mortgage|hypothecat)\b", re.I), "collateral"),
]

# Audit / deep analysis trigger patterns
_DEEP_PATTERNS = re.compile(
    r"\b(?:"
    r"review|audit|analyze|analyse|assess|evaluate|"
    r"risk\s*(?:factor|score|rating|report)|"
    r"confidence\s*(?:score|rating)|"
    r"detailed\s*report|executive\s*summary|"
    r"all\s*(?:risks|charges|fees|terms|clauses|conditions)|"
    r"comprehensive|exhaustive|full\s*(?:review|audit|report)|"
    r"red\s*flag|predatory|hidden\s*(?:charge|fee|trap)"
    r")\b",
    re.I,
)

# Calculation trigger patterns
_CALC_PATTERNS = re.compile(
    r"\b(?:"
    r"calculat|total\s*cost|how\s*much\s*(?:will|would|do)\s*i\s*pay|"
    r"amortiz|repayment\s*schedule|"
    r"if\s*i\s*(?:borrow|take|prepay|foreclose)|"
    r"scenario|what\s*(?:is|would\s*be)\s*(?:the\s*)?(?:emi|total|monthly)"
    r")\b",
    re.I,
)

# Comparison trigger patterns
_COMPARE_PATTERNS = re.compile(
    r"\b(?:compar|vs\b|versus|difference\s*between|which\s*(?:is|one)\s*(?:better|cheaper|lower))\b",
    re.I,
)

# Summary trigger patterns
_SUMMARY_PATTERNS = re.compile(
    r"\b(?:summariz|summary|overview|key\s*(?:terms|points|highlights))\b",
    re.I,
)


def classify_query_tier(query: str, intent: Optional[str] = None) -> tuple:
    """
    Classify a query into a processing tier and optionally detect the
    target financial field.

    Parameters
    ----------
    query : str
        The user's raw question.
    intent : str, optional
        Pre-classified intent from ``classify_intent()``.

    Returns
    -------
    (QueryTier, detected_field: str | None)
    """
    q = query.strip()
    q_lower = q.lower()

    # ----- 0. Out-of-scope / Unanswerable domain check -----
    from app.guardrails.answerability_guard import UNANSWERABLE_DOMAINS
    if any(term in q_lower for term in UNANSWERABLE_DOMAINS):
        return QueryTier.STANDARD_RAG, None

    # ----- 1. Deep / Audit / Risk / Comparison triggers -----
    if intent in ("review", "risk", "comparison"):
        return QueryTier.DEEP_RAG, None

    if _DEEP_PATTERNS.search(q):
        return QueryTier.DEEP_RAG, None

    if _COMPARE_PATTERNS.search(q):
        return QueryTier.DEEP_RAG, None

    # ----- 2. Calculation triggers -----
    if intent == "calculation":
        return QueryTier.CALCULATION, None

    if _CALC_PATTERNS.search(q):
        return QueryTier.CALCULATION, None

    # ----- 3. Summary triggers → STANDARD_RAG (needs retrieval but not reranker/fact-LLM) -----
    if intent == "summary" or _SUMMARY_PATTERNS.search(q):
        return QueryTier.STANDARD_RAG, None

    # ----- 4. Fast factual — short query targeting a known financial field -----
    # ----- 4. Fast factual — short query targeting a single known financial field -----
    matched_fields = []
    for pattern, field_name in _FACTUAL_FIELD_PATTERNS:
        if pattern.search(q) and field_name not in matched_fields:
            matched_fields.append(field_name)

    if len(matched_fields) > 1:
        # Compound question with multiple fields (e.g. rate and fee) → standard RAG
        return QueryTier.STANDARD_RAG, None
    elif len(matched_fields) == 1:
        field_name = matched_fields[0]
        word_count = len(q.split())
        if word_count <= 20:
            return QueryTier.FAST_FACTUAL, field_name
        else:
            return QueryTier.STANDARD_RAG, field_name

    # ----- 5. Default: STANDARD_RAG -----
    return QueryTier.STANDARD_RAG, None
