import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from app.rag.retrieval.dense_retriever import vector_search
from app.rag.retrieval.sparse_retriever import bm25_search

logger = logging.getLogger(__name__)

# Shared thread pool for parallel retrieval (2 workers: dense + sparse)
_retrieval_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="retrieval")


def compute_retrieval_agreement(
    dense_results: List[Dict[str, Any]],
    sparse_results: List[Dict[str, Any]],
    top_n: int = 3,
) -> float:
    """
    Compute rank agreement between Dense (semantic) and BM25 (keyword) retrieval.
    
    Returns a score between 0.0 and 1.0:
    - 1.0: Perfect agreement (both search engines agree on top ranked passages)
    - 0.5+: High agreement -> Safe to skip cross-encoder reranking
    - <0.5: Low agreement -> Cross-encoder reranking recommended to resolve divergence
    """
    if not dense_results or not sparse_results:
        return 0.0

    dense_top = [
        c.get("id") or c.get("chunk_id") or c.get("embedding_id")
        for c in dense_results[:top_n]
        if c.get("id") or c.get("chunk_id") or c.get("embedding_id")
    ]
    sparse_top = [
        c.get("id") or c.get("chunk_id") or c.get("embedding_id")
        for c in sparse_results[:top_n]
        if c.get("id") or c.get("chunk_id") or c.get("embedding_id")
    ]

    if not dense_top or not sparse_top:
        return 0.0

    # Top-1 exact match gives a high baseline
    top1_match = 1.0 if dense_top[0] == sparse_top[0] else 0.0
    
    # Overlap among top-N
    set_dense = set(dense_top)
    set_sparse = set(sparse_top)
    overlap = len(set_dense & set_sparse) / max(len(set_dense | set_sparse), 1)

    agreement = (0.6 * top1_match) + (0.4 * overlap)
    return round(agreement, 3)


def reciprocal_rank_fusion(
    dense_results: List[Dict[str, Any]], 
    sparse_results: List[Dict[str, Any]], 
    k: int = 60,
    top_k: int = None,
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
    
    return results[:top_k] if top_k else results


def hybrid_search(
    query: str,
    product_ids: List[str],
    top_k: int = 15,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Perform hybrid search: Dense (Pinecone) + Sparse (BM25) with RRF fusion.
    Returns top_k fused results filtered by user_id and product_ids.

    Dense and sparse retrieval run in parallel via a shared thread pool.
    Theoretical latency = max(dense, sparse) instead of dense + sparse.
    """
    dense_results = []
    sparse_results = []

    # Submit both retrievals in parallel
    future_dense = _retrieval_pool.submit(
        vector_search, query, product_ids, top_k=15, user_id=user_id
    )
    future_sparse = _retrieval_pool.submit(
        bm25_search, query, product_ids, limit=15
    )

    # Collect results (each has its own error handling internally)
    try:
        dense_results = future_dense.result(timeout=30)
    except Exception as e:
        logger.warning(f"[HybridSearch] Dense retrieval failed: {e}")

    try:
        sparse_results = future_sparse.result(timeout=30)
    except Exception as e:
        logger.warning(f"[HybridSearch] Sparse retrieval failed: {e}")

    # Compute Dense/BM25 rank agreement score
    agreement_score = compute_retrieval_agreement(dense_results, sparse_results)

    # Fuse using RRF
    fused_results = reciprocal_rank_fusion(dense_results, sparse_results)
    
    # Annotate agreement score onto results
    for chunk in fused_results:
        chunk["retrieval_agreement_score"] = agreement_score
    
    # Return top_k
    return fused_results[:top_k]