from app.rag.retrieval.dense_retriever import vector_search
from app.rag.retrieval.sparse_retriever import bm25_search
from typing import List, Dict, Any
from collections import defaultdict

def reciprocal_rank_fusion(
    dense_results: List[Dict[str, Any]], 
    sparse_results: List[Dict[str, Any]], 
    k: int = 60
) -> List[Dict[str, Any]]:
    """
    Combines dense and sparse results using RRF.
    Lower rank = better. RRF_score = sum(1 / (k + rank))
    """
    scores = defaultdict(float)
    chunk_map = {}
    
    # Process dense results
    for rank, item in enumerate(dense_results, start=1):
        chunk_id = item.get("id") or item.get("chunk_id") or item.get("embedding_id") or f"dense_{rank}"
        scores[chunk_id] += 1.0 / (k + rank)
        chunk_map[chunk_id] = item
    
    # Process sparse results
    for rank, item in enumerate(sparse_results, start=1):
        chunk_id = item.get("id") or item.get("chunk_id") or item.get("embedding_id")
        if not chunk_id:
            # Try to find by text match
            for existing_id, existing_item in chunk_map.items():
                if existing_item.get("text") == item.get("text"):
                    chunk_id = existing_id
                    break
        if not chunk_id:
            chunk_id = f"sparse_{rank}"
        
        scores[chunk_id] += 1.0 / (k + rank)
        chunk_map[chunk_id] = item
    
    # Sort by RRF score
    sorted_chunks = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    # Build final list with scores
    results = []
    for chunk_id, rrf_score in sorted_chunks:
        chunk = chunk_map.get(chunk_id, {})
        chunk["rrf_score"] = rrf_score
        results.append(chunk)
    
    return results

def hybrid_search(query: str, product_ids: List[str], top_k: int = 20) -> List[Dict[str, Any]]:
    """
    Perform hybrid search: Dense (Pinecone) + Sparse (BM25) with RRF fusion.
    Returns top_k fused results.
    """
    # Get dense results (top 30)
    dense_results = vector_search(query, product_ids, top_k=30)
    
    # Get sparse results (top 30)
    sparse_results = bm25_search(query, product_ids, limit=30)
    
    # Fuse using RRF
    fused_results = reciprocal_rank_fusion(dense_results, sparse_results)
    
    # Return top_k
    return fused_results[:top_k]