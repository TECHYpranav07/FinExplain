from typing import List, Dict, Any

def compute_mrr(retrieved_chunk_ids: List[str], ground_truth_chunk_ids: List[str]) -> float:
    """Mean Reciprocal Rank (MRR)."""
    for rank, chunk_id in enumerate(retrieved_chunk_ids, start=1):
        if chunk_id in ground_truth_chunk_ids:
            return 1.0 / rank
    return 0.0

def compute_recall_at_k(retrieved_chunk_ids: List[str], ground_truth_chunk_ids: List[str], k: int = 5) -> float:
    """Recall@K."""
    if not ground_truth_chunk_ids:
        return 1.0
    hits = sum(1 for cid in retrieved_chunk_ids[:k] if cid in ground_truth_chunk_ids)
    return hits / len(ground_truth_chunk_ids)

def compute_citation_precision(citations: List[Dict[str, Any]]) -> float:
    """Fraction of citations that are verified against ground context."""
    if not citations:
        return 1.0
    verified = sum(1 for c in citations if c.get("verified", False))
    return verified / len(citations)
