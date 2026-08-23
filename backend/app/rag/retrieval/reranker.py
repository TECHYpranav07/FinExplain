import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Load cross-encoder once
_reranker = None
_reranker_failed = False

# Minimum RRF score to qualify for expensive cross-encoder reranking.
# Candidates below this are discarded before the CPU-bound forward pass.
MIN_RRF_SCORE_FOR_RERANK = 0.012


def get_reranker():
    global _reranker, _reranker_failed
    if _reranker_failed:
        return None
    if _reranker is None:
        try:
            # Keep heavyweight ML dependency out of startup; load on demand
            from sentence_transformers import CrossEncoder
            _reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        except Exception as e:
            logger.warning(f"[Reranker] CrossEncoder unavailable ({e}). Falling back to retrieval rank order.")
            _reranker_failed = True
            return None
    return _reranker

def rerank_chunks(query: str, chunks: List[Dict[str, Any]], top_k: int = 6) -> List[Dict[str, Any]]:
    """
    Re-ranks chunks using a cross-encoder for precise relevance scoring.

    Optimizations over the original implementation:
    1. Pre-filters candidates by RRF score to reduce the number of
       expensive cross-attention forward passes (20 → ~8 pairs).
    2. Reduced default ``top_k`` from 10 → 6.
    3. Falls back gracefully to retrieval score order if CrossEncoder fails.
    """
    if not chunks:
        return []

    # Pre-filter: only send candidates with meaningful RRF scores to the
    # cross-encoder.  This typically cuts the pool from ~15 down to 8-10,
    # reducing CPU inference time proportionally.
    candidates = [
        c for c in chunks
        if c.get("rrf_score", 1.0) >= MIN_RRF_SCORE_FOR_RERANK
    ]
    # Always keep at least top_k candidates even if RRF scores are low
    if len(candidates) < top_k:
        candidates = chunks[:max(top_k, len(chunks))]
    # Cap at 10 to bound CPU cost
    candidates = candidates[:10]

    reranker = get_reranker()
    if reranker is not None:
        try:
            # Prepare pairs for cross-encoder
            pairs = [(query, chunk.get("text", "")) for chunk in candidates]
            scores = reranker.predict(pairs)
            
            for i, chunk in enumerate(candidates):
                chunk["rerank_score"] = float(scores[i])
            
            sorted_chunks = sorted(candidates, key=lambda x: x.get("rerank_score", 0), reverse=True)
            return sorted_chunks[:top_k]
        except Exception as e:
            logger.warning(f"[Reranker] Inference failed ({e}), using retrieval ranking.")

    # Graceful fallback: maintain existing ranking and assign synthetic rerank scores
    for i, chunk in enumerate(candidates):
        if "rerank_score" not in chunk:
            # Synthetic score decaying with retrieval rank
            chunk["rerank_score"] = max(0.1, 0.9 - (i * 0.05))
    
    return candidates[:top_k]
