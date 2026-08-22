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
        if not retrieved_chunks:
            logger.info("[AnswerabilityGate] No chunks retrieved. Aborting generation early.")
            return (
                False,
                "No relevant document sections found matching this inquiry in the uploaded agreements."
            )

        if rerank_scores and max(rerank_scores) < MIN_RETRIEVAL_CONFIDENCE and len(retrieved_chunks) < 2:
            logger.info(f"[AnswerabilityGate] Low retrieval score ({max(rerank_scores):.3f}). Insufficient evidence.")
            return (
                False,
                "Retrieved document context does not contain sufficient confidence to answer this specific query."
            )

        return True, "Sufficient evidence available"


answerability_gate = AnswerabilityGate()
