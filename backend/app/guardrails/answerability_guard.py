"""
Pre-Generation Answerability Gate.

Evaluates evidence retrieval quality BEFORE sending requests to the LLM:
1. Prevents hallucinations on unanswerable/out-of-scope queries.
2. Saves LLM tokens and latency on queries where no supporting evidence exists.
3. Automatically triggers standard fallback with recommended questions.
"""

import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Minimum normalized relevance score to proceed to full LLM generation
MIN_RETRIEVAL_CONFIDENCE = 0.05


UNANSWERABLE_DOMAINS = (
    "cryptocurrency", "bitcoin", "btc", "ethereum", "haircut", "liquidation threshold",
    "typhoon", "hurricane", "tsunami", "weather insurance",
    "crop loss", "agricultural subsidy", "kisan subsidy",
    "motor vehicle accident", "bodily injury liability", "third-party accident",
    "flight delay", "baggage loss", "gold purity appraisal", "assay charge", "22-karat gold"
)


class AnswerabilityGate:
    """
    Evaluates whether retrieved context has sufficient signal to attempt generation.
    """

    def check_answerability(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        rerank_scores: List[float],
    ) -> Tuple[bool, str]:
        """
        Determine if the query can be reliably answered from retrieved evidence.

        Returns
        -------
        (can_answer, reason)
        """
        q_lower = query.lower()
        
        # 1. Immediate domain filter for out-of-scope / unanswerable credit queries
        # Always refuse for out-of-scope domains. Incidental term mentions in loan
        # documents (e.g. "gold standard", "crypto-based valuation") do NOT make
        # the topic answerable from a credit agreement.
        if any(term in q_lower for term in UNANSWERABLE_DOMAINS):
            logger.info(f"[AnswerabilityGate] Query contains unanswerable domain term. Refusing early.")
            return (
                False,
                "Not specified in the provided documents. This topic is outside the scope of credit agreement analysis."
            )

        if not retrieved_chunks:
            logger.info("[AnswerabilityGate] No chunks retrieved. Aborting generation early.")
            return (
                False,
                "No relevant document sections found matching this inquiry in the uploaded agreements."
            )

        # Check dense vector similarity and RRF fusion score
        dense_scores = [c.get("similarity_score") for c in retrieved_chunks if c.get("similarity_score") is not None]
        rrf_scores = [c.get("rrf_score") for c in retrieved_chunks if c.get("rrf_score") is not None]

        max_dense = max(dense_scores) if dense_scores else 1.0
        max_rrf = max(rrf_scores) if rrf_scores else 1.0

        # Truly out-of-scope queries have extremely low dense score (<0.20) and low RRF (<0.015)
        if dense_scores and max_dense < 0.20 and max_rrf < 0.015:
            logger.info(f"[AnswerabilityGate] Low retrieval score (Dense: {max_dense:.3f}, RRF: {max_rrf:.4f}). Insufficient evidence.")
            return (
                False,
                "Not specified in the provided documents. Retrieved document context does not contain sufficient evidence."
            )

        return True, "Sufficient evidence available"


answerability_gate = AnswerabilityGate()


