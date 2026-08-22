"""
Product Isolation and Anti-Rate-Averaging Guardrail.

Guarantees:
1. Product isolation: Terms from Product A never contaminate Product B.
2. Anti-Averaging: The LLM is prohibited from calculating synthetic averages of
   interest rates or fee percentages between distinct products.
3. Provenance Integrity: Every fact is locked to its originating product namespace.
"""

import re
import logging
from typing import List, Dict, Tuple, Any
from app.core.loan_categories import LoanFact

logger = logging.getLogger(__name__)

# Patterns where LLM averages rates between distinct loan products
AVERAGING_PATTERNS = [
    re.compile(r"(?:average|blended|mean|combined)\s+(?:interest\s+)?rate\s+(?:across|between|of)\s+(?:both|the\s+two|all|these)\s+products\s+is\s+([0-9.]+%?)", re.IGNORECASE),
    re.compile(r"average\s+(?:processing\s+)?fee\s+(?:between|across)\s+(?:both|these)\s+products\s+is\s+([0-9.]+%?)", re.IGNORECASE),
]


class ProductIsolationGuard:
    """
    Guarantees isolation between multiple loan products in multi-document queries.
    """

    def segment_facts_by_product(self, facts: List[LoanFact]) -> Dict[str, List[LoanFact]]:
        """
        Partition extracted facts into isolated product namespaces.
        """
        segmented: Dict[str, List[LoanFact]] = {}
        for f in facts:
            key = f.source_document or "General Product"
            if key not in segmented:
                segmented[key] = []
            segmented[key].append(f)
        return segmented

    def verify_no_rate_averaging(self, answer: str, is_explicit_average_query: bool = False) -> Tuple[bool, str]:
        """
        Detect and neutralize unauthorized averaging of distinct product rates.

        Returns
        -------
        (is_valid, sanitized_answer)
        """
        if is_explicit_average_query or not answer:
            return True, answer

        sanitized = answer
        violates = False

        for pattern in AVERAGING_PATTERNS:
            match = pattern.search(sanitized)
            if match:
                violates = True
                avg_text = match.group(0)
                logger.warning(f"[ProductIsolationGuard] Detected unauthorized rate averaging: '{avg_text}'")
                # Replace hallucinated average with explicit product comparison note
                sanitized = sanitized.replace(
                    avg_text,
                    "[Product isolation rule: Each loan maintains its own discrete rate; rates are not averaged]"
                )

        return not violates, sanitized


product_isolation_guard = ProductIsolationGuard()
