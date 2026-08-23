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
from typing import List, Optional

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

# Aspects that require more than a single structured fact. These are kept
# separate from _FACTUAL_FIELD_PATTERNS because a query can mention one fact
# and still request several contractual qualifiers around it.
_QUERY_ASPECT_PATTERNS = [
    (re.compile(r"\b(?:interest\s*rate|rate\s*of\s*interest|roi|annual\s*rate)\b", re.I), "interest_rate"),
    (re.compile(r"\b(?:fixed|floating|variable|adjustable|benchmark|reference\s*rate|spread|rate\s*type)\b", re.I), "rate_type_or_benchmark"),
    (re.compile(r"\b(?:processing|administrative|origination|upfront)\s*(?:fee|charge)s?\b", re.I), "processing_fee"),
    (re.compile(r"\b(?:other|additional|applicable)\s*(?:fees?|charges?)\b", re.I), "other_charges"),
    (re.compile(r"\b(?:gst|tax(?:es)?|lev(?:y|ies)|stamp\s*duty|statutory)\b", re.I), "taxes_and_levies"),
    (re.compile(r"\b(?:prepayment|foreclosure|early\s*(?:closure|repayment|settlement))\b", re.I), "prepayment_or_foreclosure"),
    (re.compile(r"\b(?:lock[\s-]?in|cooling[\s-]?off|look[\s-]?up|emi(?:s)?|financial\s*year)\b", re.I), "timing_or_lock_in"),
    (re.compile(r"\b(?:notice|written\s*request|procedure|conditions?)\b", re.I), "procedure_and_conditions"),
    (re.compile(r"\b(?:eligib(?:ility|le)|individual\s*borrower|business\s*purpose|except|unless|waiver|exception)\b", re.I), "eligibility_and_exceptions"),
    (re.compile(r"\b(?:default|penal|overdue|delayed\s*payment)\b", re.I), "default_or_penal_charges"),
    (re.compile(r"\b(?:bounce|ecs|cheque|check)\b", re.I), "bounce_charges"),
    (re.compile(r"\b(?:epi|equated\s*(?:monthly\s*)?install?ment)\b", re.I), "epi_calculation"),
    (re.compile(r"\b(?:repayment|install?ment|amortization|schedule)\b", re.I), "repayment_terms"),
    (re.compile(r"\b(?:how\s+is\s+interest|daily|365|actual\s*days|monthly\s*rests?|day[- ]count)\b", re.I), "calculation_basis"),
    (re.compile(r"\b(?:security|collateral|mortgage|hypothecat)\b", re.I), "security_or_mortgage"),
    (re.compile(r"\b(?:insurance|insured|policy)\b", re.I), "insurance"),
    (re.compile(r"\b(?:governing\s*law|jurisdiction|arbitration|dispute|court|tribunal)\b", re.I), "governing_law_or_disputes"),
]

_QUALIFIER_PATTERN = re.compile(
    r"\b(?:conditions?|terms?|options?|applicable|specific|detailed|how|what\s+happens|who\s+bears)\b",
    re.I,
)

_ANSWER_REQUIREMENT_PATTERNS = {
    "interest_rate": re.compile(r"\b(?:interest\s*rate|rate\s*of\s*interest|roi)\b|\b\d+(?:\.\d+)?\s*(?:%|percent)", re.I),
    "rate_type_or_benchmark": re.compile(r"\b(?:fixed|floating|variable|adjustable|benchmark|reference\s*rate|spread)\b", re.I),
    "processing_fee": re.compile(r"\b(?:processing|administrative|origination|upfront)\s*(?:fee|charge)s?\b", re.I),
    "other_charges": re.compile(r"\b(?:fee|fees|charge|charges|costs?)\b", re.I),
    "taxes_and_levies": re.compile(r"\b(?:gst|tax(?:es)?|lev(?:y|ies)|stamp\s*duty|statutory)\b", re.I),
    "prepayment_or_foreclosure": re.compile(r"\b(?:prepayment|foreclosure|early\s*(?:closure|repayment|settlement))\b", re.I),
    "timing_or_lock_in": re.compile(r"\b(?:lock[\s-]?in|cooling[\s-]?off|look[\s-]?up|after\s+\d+\s*emis?|\d+\s*days?|financial\s*year|monthly)\b", re.I),
    "procedure_and_conditions": re.compile(r"\b(?:condition|terms?|applicable|subject\s+to|only|except|unless|provided|notice|request|procedure|after|before|within|until)\b", re.I),
    "eligibility_and_exceptions": re.compile(r"\b(?:eligib(?:ility|le)|individual\s*borrower|business\s*purpose|except|unless|waiver|exception)\b", re.I),
    "default_or_penal_charges": re.compile(r"\b(?:default|penal|overdue|delayed\s*payment)\b", re.I),
    "bounce_charges": re.compile(r"\b(?:bounce|ecs|cheque|check)\b", re.I),
    "epi_calculation": re.compile(r"\b(?:epi|equated\s*(?:monthly\s*)?install?ment)\b", re.I),
    "repayment_terms": re.compile(r"\b(?:repayment|install?ment|amortization|schedule)\b", re.I),
    "calculation_basis": re.compile(r"\b(?:calculat|daily|365|actual\s*days|monthly\s*rests?)\b", re.I),
    "security_or_mortgage": re.compile(r"\b(?:security|collateral|mortgage|hypothecat)\b", re.I),
    "insurance": re.compile(r"\b(?:insurance|insured|policy)\b", re.I),
    "governing_law_or_disputes": re.compile(r"\b(?:governing\s*law|jurisdiction|arbitration|dispute|court|tribunal)\b", re.I),
}


def extract_query_requirements(query: str) -> List[str]:
    """Return the contractual answer dimensions requested by *query*."""
    requirements: List[str] = []
    for pattern, requirement in _QUERY_ASPECT_PATTERNS:
        if pattern.search(query) and requirement not in requirements:
            requirements.append(requirement)

    # A qualifier turns a headline lookup into a conditions question even if
    # the query names only one financial field.
    has_repayment_terms = bool(re.search(r"\brepayment\s+terms?\b", query, re.I))
    if requirements and _QUALIFIER_PATTERN.search(query) and not has_repayment_terms and "procedure_and_conditions" not in requirements:
        requirements.append("procedure_and_conditions")
    return requirements


def is_compound_query(query: str) -> bool:
    """Identify queries that must not use the single-fact fast path."""
    requirements = extract_query_requirements(query)
    return len(requirements) > 1 or bool(
        re.search(r"\b(?:and|or|as\s+well\s+as|along\s+with)\b", query, re.I)
        and _QUALIFIER_PATTERN.search(query)
    )


def missing_answer_requirements(answer: str, requirements: List[str]) -> List[str]:
    """Return requested dimensions not visibly addressed by an answer."""
    answer_text = answer or ""
    return [
        requirement
        for requirement in requirements
        if requirement in _ANSWER_REQUIREMENT_PATTERNS
        and not _ANSWER_REQUIREMENT_PATTERNS[requirement].search(answer_text)
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
    if is_compound_query(q):
        # Compound questions need retrieval plus a checklist-aware answer;
        # returning one LoanFact here silently drops requested sub-answers.
        return QueryTier.STANDARD_RAG, None

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
