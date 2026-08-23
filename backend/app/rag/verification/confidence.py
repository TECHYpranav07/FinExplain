"""
Deterministic evidence-quality scoring for FinExplain.

Two scoring systems coexist:
1. ``calculate_confidence()`` — original multi-dimensional confidence score
   (backward-compatible, retained for the orchestrator).
2. ``EvidenceScorer`` — new configurable 0–100 evidence-quality score with
   per-dimension breakdown and hallucination penalties.

The LLM must NEVER directly choose the final score.
"""

from typing import List, Dict, Any, Optional


# =========================================================================
# 1. Original confidence calculation (backward-compatible)
# =========================================================================

def calculate_confidence(
    retrieved_chunks: List[Dict[str, Any]],
    rerank_scores: List[float],
    citation_coverage: float,
    conflicts_detected: bool,
) -> Dict[str, Any]:
    """
    Calculate multi-dimensional confidence score.
    """
    # Factor 1: Chunk count (cap at 5)
    chunk_factor = min(len(retrieved_chunks) / 5, 1.0)

    # Factor 2: Average rerank score
    if rerank_scores:
        avg_rerank = sum(rerank_scores) / len(rerank_scores)
    else:
        avg_rerank = 0.5

    # Factor 3: Citation coverage
    citation_factor = citation_coverage

    # Factor 4: Conflict penalty
    conflict_penalty = 0.15 if conflicts_detected else 0.0

    # Weighted average
    raw_score = (
        (0.25 * chunk_factor)
        + (0.35 * avg_rerank)
        + (0.40 * citation_factor)
        - conflict_penalty
    )

    score = max(0.0, min(1.0, raw_score))

    # Determine label
    if score >= 0.75:
        label = "High"
    elif score >= 0.50:
        label = "Medium"
    else:
        label = "Low"

    return {
        "score": score,
        "label": label,
        "factors": {
            "chunk_factor": chunk_factor,
            "avg_rerank": avg_rerank,
            "citation_coverage": citation_factor,
            "conflict_penalty": conflict_penalty,
        },
    }


# =========================================================================
# 2. New configurable evidence-quality scorer (0–100)
# =========================================================================

# Default weights — intentionally configurable
DEFAULT_WEIGHTS: Dict[str, int] = {
    "citation_validity": 20,
    "claim_evidence_support": 25,
    "retrieval_relevance": 10,
    "source_quality": 10,
    "condition_preservation": 10,
    "conflict_free": 10,
    "missing_information": 5,
    "calculation_validity": 10,
}

# Hallucination penalty config
UNSUPPORTED_CLAIM_PENALTY: int = 25
MAX_CONFIDENCE_WITH_UNSUPPORTED: float = 0.59


class EvidenceScorer:
    """
    Deterministic multi-dimensional evidence-quality scorer.

    Produces a 0–100 score with per-dimension breakdown.
    Applies hallucination penalties for unsupported material claims.
    Rewards correct uncertainty handling (saying "Not specified").
    """

    def __init__(self, weights: Optional[Dict[str, int]] = None):
        self.weights = weights or dict(DEFAULT_WEIGHTS)

    def calculate_evidence_score(
        self,
        claim_results: Optional[Dict[str, Any]] = None,
        facts: Optional[List[Any]] = None,
        conflicts: Optional[List[Dict[str, Any]]] = None,
        missing: Optional[List[Dict[str, Any]]] = None,
        calculation_result: Optional[Dict[str, Any]] = None,
        rerank_scores: Optional[List[float]] = None,
        is_meta_query: bool = False,
    ) -> Dict[str, Any]:
        """
        Compute the evidence-quality score.

        Parameters
        ----------
        claim_results : output of ``verify_all_claims()``
        facts : list of ``LoanFact`` objects
        conflicts : list of conflict dicts
        missing : list of missing-information dicts
        calculation_result : output of ``calculate_loan_scenario()``
        rerank_scores : list of rerank scores from the retrieval step
        is_meta_query : whether this is a risk/audit/summary meta query

        Returns
        -------
        ::

            {
                "score": 78,
                "score_normalized": 0.78,
                "label": "High",
                "dimensions": { ... },
                "penalties": { ... },
                "details": "...",
            }
        """
        claim_results = claim_results or {}
        facts = facts or []
        conflicts = conflicts or []
        missing = missing or []

        dimensions: Dict[str, float] = {}

        # ---- Citation validity (max = weight) ----
        w = self.weights["citation_validity"]
        total_claims = claim_results.get("total_claims", 0)
        invalid_cites = claim_results.get("invalid_citations", 0)
        if total_claims > 0:
            valid_ratio = 1.0 - (invalid_cites / total_claims)
            dimensions["citation_validity"] = round(w * valid_ratio, 2)
        elif is_meta_query:
            dimensions["citation_validity"] = float(w)
        else:
            dimensions["citation_validity"] = round(w * 0.5, 2)  # neutral

        # ---- Claim evidence support (max = weight) ----
        w = self.weights["claim_evidence_support"]
        coverage = claim_results.get("claim_coverage", 0.0)
        if is_meta_query and facts:
            dimensions["claim_evidence_support"] = float(w)
        elif coverage >= 0.9:
            dimensions["claim_evidence_support"] = float(w)
        elif coverage >= 0.6:
            dimensions["claim_evidence_support"] = round(w * 0.6, 2)
        elif coverage >= 0.3:
            dimensions["claim_evidence_support"] = round(w * 0.3, 2)
        else:
            dimensions["claim_evidence_support"] = 0.0


        # ---- Retrieval relevance (max = weight) ----
        w = self.weights["retrieval_relevance"]
        if rerank_scores:
            avg_rerank = sum(rerank_scores) / len(rerank_scores)
            # Normalize rerank score (cross-encoder scores vary, typically -10 to +10)
            normalized = max(0.0, min(1.0, (avg_rerank + 5) / 10))
            dimensions["retrieval_relevance"] = round(w * normalized, 2)
        else:
            dimensions["retrieval_relevance"] = round(w * 0.5, 2)

        # ---- Source quality (max = weight) ----
        w = self.weights["source_quality"]
        # Score based on number of facts with page/section metadata
        if facts:
            with_metadata = sum(
                1 for f in facts if f.page is not None or f.section is not None
            )
            meta_ratio = with_metadata / len(facts)
            dimensions["source_quality"] = round(w * meta_ratio, 2)
        else:
            dimensions["source_quality"] = 0.0

        # ---- Condition preservation (max = weight) ----
        w = self.weights["condition_preservation"]
        conditions_dropped = claim_results.get("conditions_dropped", 0)
        if total_claims > 0:
            preserved_ratio = 1.0 - (conditions_dropped / total_claims)
            dimensions["condition_preservation"] = round(w * preserved_ratio, 2)
        else:
            dimensions["condition_preservation"] = float(w)

        # ---- Conflict-free (max = weight) ----
        w = self.weights["conflict_free"]
        if not conflicts:
            dimensions["conflict_free"] = float(w)
        else:
            # Conflicts exist but are surfaced (5/10) vs hidden (0/10)
            # Since we always surface conflicts, give partial credit
            dimensions["conflict_free"] = round(w * 0.5, 2)

        # ---- Missing information (max = weight) ----
        w = self.weights["missing_information"]
        # IMPORTANT: Correctly detecting missing info is GOOD.
        # We reward correct uncertainty, not penalise it.
        if not missing:
            dimensions["missing_information"] = float(w)
        else:
            # Missing info exists but was correctly identified
            dimensions["missing_information"] = float(w)

        # ---- Calculation validity (max = weight) ----
        w = self.weights["calculation_validity"]
        if calculation_result is None:
            # No calculation needed — full marks
            dimensions["calculation_validity"] = float(w)
        else:
            unknown = calculation_result.get("unknown_costs", [])
            if not unknown:
                dimensions["calculation_validity"] = float(w)
            elif len(unknown) <= 2:
                dimensions["calculation_validity"] = round(w * 0.5, 2)
            else:
                dimensions["calculation_validity"] = 0.0

        # ---- Raw score ----
        raw_score = sum(dimensions.values())

        # ---- Penalties ----
        penalties: Dict[str, float] = {}
        unsupported = claim_results.get("unsupported_claims", 0)
        if unsupported > 0:
            penalty = min(UNSUPPORTED_CLAIM_PENALTY * unsupported, 50)
            penalties["unsupported_claims"] = penalty
            raw_score -= penalty

        final_score = max(0, min(100, round(raw_score)))

        # Cap confidence if material claims are unsupported
        if unsupported > 0:
            final_score = min(final_score, int(MAX_CONFIDENCE_WITH_UNSUPPORTED * 100))

        # Label
        if final_score >= 75:
            label = "High"
        elif final_score >= 50:
            label = "Medium"
        else:
            label = "Low"

        return {
            "score": final_score,
            "score_normalized": round(final_score / 100.0, 3),
            "label": label,
            "dimensions": dimensions,
            "penalties": penalties,
            "details": f"Evidence score {final_score}/100 across {len(dimensions)} dimensions.",
        }


# Singleton for convenience
evidence_scorer = EvidenceScorer()