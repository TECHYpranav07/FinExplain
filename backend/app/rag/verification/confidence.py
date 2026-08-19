from typing import List, Dict, Any

def calculate_confidence(
    retrieved_chunks: List[Dict[str, Any]],
    rerank_scores: List[float],
    citation_coverage: float,
    conflicts_detected: bool
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
    raw_score = (0.25 * chunk_factor) + (0.35 * avg_rerank) + (0.40 * citation_factor) - conflict_penalty
    
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
            "conflict_penalty": conflict_penalty
        }
    }