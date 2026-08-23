"""
Deterministic conditional-language detection.

Scans text for financially significant conditional phrases and annotates
``LoanFact`` objects whose status the LLM may have incorrectly set to
EXPLICIT when the source text contains conditional language.

No LLM calls — pure Python string analysis.
"""

import re
from typing import List, Dict, Any, Optional

from app.core.loan_categories import LoanFact, EvidenceStatus


# ---------------------------------------------------------------------------
# Conditional phrase catalogue
# ---------------------------------------------------------------------------

CONDITIONAL_PHRASES: List[str] = [
    "if",
    "when",
    "after",
    "before",
    "within",
    "only",
    "subject to",
    "provided that",
    "only if",
    "unless otherwise",
    "waived after",
    "waived if",
    "applicable when",
    "in the event of",
    "upon default",
    "prior written notice",
    "not exceeding",
    "lock-in of",
    "lock in of",
    "plus applicable",
    "subject to rbi",
    "as per regulatory",
    "contingent upon",
    "depending on",
    "minimum of",
    "maximum of",
    "at least",
]

# Pre-compile a single regex that matches any of the phrases as whole words
_PHRASE_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in CONDITIONAL_PHRASES) + r")\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_conditions(text: str) -> List[Dict[str, Any]]:
    """
    Scan *text* for conditional phrases.

    Returns a list of matches::

        [
            {
                "phrase": "waived after",
                "context": "...fee is waived after 12 months...",
                "position": 42,
            },
            ...
        ]
    """
    if not text:
        return []

    results: List[Dict[str, Any]] = []
    for match in _PHRASE_PATTERN.finditer(text):
        start = max(0, match.start() - 30)
        end = min(len(text), match.end() + 30)
        results.append({
            "phrase": match.group(0).lower(),
            "context": text[start:end].strip(),
            "position": match.start(),
        })
    return results


def annotate_facts_with_conditions(
    facts: List[LoanFact],
    chunks: Optional[List[Dict[str, Any]]] = None,
) -> List[LoanFact]:
    """
    Deterministically check whether each fact's ``source_text`` contains
    conditional language.  If it does and the fact's status is currently
    ``EXPLICIT``, upgrade it to ``CONDITIONAL``.

    Parameters
    ----------
    facts : list of LoanFact
    chunks : optional list of chunk dicts (unused today, reserved for
             future cross-chunk condition propagation)

    Returns
    -------
    The same list of facts, mutated in-place.
    """
    for fact in facts:
        text_to_check = fact.source_text or ""
        if fact.condition:
            text_to_check += " " + fact.condition

        conditions = detect_conditions(text_to_check)
        if conditions and fact.status == EvidenceStatus.EXPLICIT:
            fact.status = EvidenceStatus.CONDITIONAL
            # If no condition string was set by the LLM, synthesise one from
            # the detected phrase context
            if not fact.condition:
                fact.condition = conditions[0]["context"]

    return facts
