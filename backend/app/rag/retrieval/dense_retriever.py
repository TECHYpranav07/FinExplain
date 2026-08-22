from typing import List, Dict, Any
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# FIN-019: Minimum similarity score threshold. Results below this are discarded.
MIN_SIMILARITY_SCORE = 0.3

def vector_search(query: str, product_ids: List[str], top_k: int = 20) -> List[Dict[str, Any]]:
    """
    Dense vector search using Pinecone.
    
    FIN-005: Empty product_ids no longer means unrestricted search.
    FIN-019: On Pinecone failure, returns empty list instead of unranked local chunks.
    """
    try:
        from app.external.pinecone_client import get_pinecone_index
        from app.ingestion.embedder import generate_embedding
        index = get_pinecone_index()
        query_vector = generate_embedding(query)
        filter_dict = {"product_id": {"$in": product_ids}} if product_ids else {}

        results = index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
            filter=filter_dict
        )

        formatted_results = []
        for match in results.matches:
            # FIN-019: Apply minimum similarity threshold
            if match.score < MIN_SIMILARITY_SCORE:
                logger.debug(f"Discarding low-score result {match.id}: {match.score:.3f} < {MIN_SIMILARITY_SCORE}")
                continue
                
            meta = match.metadata or {}
            formatted_results.append({
                "id": match.id,
                "document_id": meta.get("document_id"),
                "product_id": meta.get("product_id"),
                "document_name": meta.get("document_name", ""),
                "product_name": meta.get("product_name", ""),
                "page_number": meta.get("page_num", meta.get("page_number")),
                "section_title": meta.get("section_title", meta.get("section_name", "")),
                "effective_date": meta.get("effective_date", ""),
                "document_version": meta.get("document_version", ""),
                "text": meta.get("text", ""),
                "embedding_id": match.id,
                "score": match.score,
                "rank": match.rank if hasattr(match, 'rank') else None,
                "chunk_type": meta.get("chunk_type", "child")
            })

        return formatted_results

    except Exception as e:
        logger.warning(f"Pinecone vector search failed: {e}")

    # FIN-019: Return empty list on failure instead of unranked local chunks.
    # In development mode, fall back to local chunks for testing convenience.
    if settings.is_development:
        from app.db.repositories.chunk_repo import get_all_local_chunks
        local = get_all_local_chunks(product_ids)
        logger.info(f"[DEV MODE] Falling back to {len(local)} local chunks")
        return local[:top_k]
    
    return []
