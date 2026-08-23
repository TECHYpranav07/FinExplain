"""
Lightweight Cloud-Optimized Reranker for FinExplain.

Performs relevance ranking using combined RRF scores and BM25 term alignment
without loading heavy local ML models or causing OOM/CPU spikes on Render free-tier.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

MIN_RRF_SCORE_FOR_RERANK = 0.012


def get_reranker():
    """Compatibility interface for unit test mocking."""
    return None


def rerank_chunks(query: str, chunks: List[Dict[str, Any]], top_k: int = 6) -> List[Dict[str, Any]]:
    """
    Rerank chunks using retrieval score fusion and term alignment.
    Guaranteed zero-memory, zero-GPU execution for Render free-tier.
    """
    if not chunks:
        return []

    candidates = [
        c for c in chunks
        if c.get("rrf_score", 1.0) >= MIN_RRF_SCORE_FOR_RERANK
    ]
    if len(candidates) < top_k:
        candidates = chunks[:max(top_k, len(chunks))]

    query_words = set(query.lower().split())

    scored_candidates = []
    for i, chunk in enumerate(candidates):
        rrf = chunk.get("rrf_score", 0.0)
        text = (chunk.get("text") or "").lower()
        chunk_words = set(text.split())
        overlap = len(query_words & chunk_words) / max(len(query_words), 1)

        # Combined score: RRF base + lexical alignment boost
        rank_score = (rrf * 10.0) + (overlap * 0.5) + max(0.1, 0.5 - (i * 0.05))
        chunk["rerank_score"] = round(float(rank_score), 4)
        scored_candidates.append((rank_score, chunk))

    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored_candidates[:top_k]]
