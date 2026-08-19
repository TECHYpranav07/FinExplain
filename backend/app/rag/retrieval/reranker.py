from sentence_transformers import CrossEncoder
from typing import List, Dict, Any

# Load cross-encoder once
_reranker = None

def get_reranker():
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    return _reranker

def rerank_chunks(query: str, chunks: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
    """
    Re-ranks chunks using a cross-encoder for precise relevance scoring.
    """
    if not chunks:
        return []
    
    reranker = get_reranker()
    
    # Prepare pairs for cross-encoder
    pairs = [(query, chunk.get("text", "")) for chunk in chunks]
    
    # Get scores
    scores = reranker.predict(pairs)
    
    # Add scores to chunks
    for i, chunk in enumerate(chunks):
        chunk["rerank_score"] = float(scores[i])
    
    # Sort by rerank score (higher is better)
    sorted_chunks = sorted(chunks, key=lambda x: x.get("rerank_score", 0), reverse=True)
    
    return sorted_chunks[:top_k]