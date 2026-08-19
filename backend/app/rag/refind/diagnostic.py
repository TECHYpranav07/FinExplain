from typing import Dict, Any, List

def diagnose_retrieval_failure(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
    confidence_score: float,
    conflicts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Diagnose why a RAG query failed or resulted in low confidence.
    """
    diagnosis = {
        "query": query,
        "chunk_count": len(retrieved_chunks),
        "confidence_score": confidence_score,
        "has_conflicts": len(conflicts) > 0,
        "failure_reasons": []
    }

    if len(retrieved_chunks) == 0:
        diagnosis["failure_reasons"].append("ZERO_CHUNKS_RETRIEVED")
    elif len(retrieved_chunks) < 3:
        diagnosis["failure_reasons"].append("INSUFFICIENT_EVIDENCE")

    if confidence_score < 0.5:
        diagnosis["failure_reasons"].append("LOW_CONFIDENCE_SCORE")

    if len(conflicts) > 0:
        diagnosis["failure_reasons"].append("DOCUMENT_CONTRADICTIONS_FOUND")

    return diagnosis
