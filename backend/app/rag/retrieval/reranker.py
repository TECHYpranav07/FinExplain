import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Load cross-encoder once
_reranker = None
_reranker_failed = False

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

def rerank_chunks(query: str, chunks: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
    """
    Re-ranks chunks using a cross-encoder for precise relevance scoring.
    FIN-009, FIN-022: Falls back gracefully to retrieval score order if CrossEncoder fails.
    """
    if not chunks:
        return []
    
    reranker = get_reranker()
    if reranker is not None:
        try:
            # Prepare pairs for cross-encoder
            pairs = [(query, chunk.get("text", "")) for chunk in chunks]
            scores = reranker.predict(pairs)
            
            for i, chunk in enumerate(chunks):
                chunk["rerank_score"] = float(scores[i])
            
            sorted_chunks = sorted(chunks, key=lambda x: x.get("rerank_score", 0), reverse=True)
            return sorted_chunks[:top_k]
        except Exception as e:
            logger.warning(f"[Reranker] Inference failed ({e}), using retrieval ranking.")

    # Graceful fallback: maintain existing ranking and assign synthetic rerank scores
    for i, chunk in enumerate(chunks):
        if "rerank_score" not in chunk:
            # Synthetic score decaying with retrieval rank
            chunk["rerank_score"] = max(0.1, 0.9 - (i * 0.05))
    
    return chunks[:top_k]
