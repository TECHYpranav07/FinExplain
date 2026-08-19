import numpy as np
from typing import List, Dict, Any

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    a = np.array(vec1)
    b = np.array(vec2)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(np.dot(a, b) / norm)

def mmr_deduplicate(
    query_embedding: List[float],
    candidate_chunks: List[Dict[str, Any]],
    top_k: int = 10,
    lambda_param: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Maximal Marginal Relevance (MMR) deduplication to balance relevance and diversity.
    lambda_param: 1.0 means purely relevance-driven, 0.0 means purely diversity-driven.
    """
    if not candidate_chunks:
        return []
    if len(candidate_chunks) <= top_k:
        return candidate_chunks

    selected: List[Dict[str, Any]] = []
    unselected = list(candidate_chunks)

    while len(selected) < top_k and unselected:
        best_score = -float("inf")
        best_candidate_idx = 0

        for idx, candidate in enumerate(unselected):
            emb = candidate.get("embedding")
            if not emb:
                # If embeddings are missing, use rerank_score or rank
                score = candidate.get("rerank_score", 0.5)
            else:
                rel_score = cosine_similarity(query_embedding, emb)
                div_score = 0.0
                if selected:
                    div_score = max(
                        cosine_similarity(emb, s.get("embedding", emb))
                        for s in selected
                    )
                score = lambda_param * rel_score - (1.0 - lambda_param) * div_score

            if score > best_score:
                best_score = score
                best_candidate_idx = idx

        selected.append(unselected.pop(best_candidate_idx))

    return selected
