from typing import List, Dict, Any
import logging
from app.db.repositories.chunk_repo import get_all_local_chunks

logger = logging.getLogger(__name__)

def vector_search(query: str, product_ids: List[str], top_k: int = 20) -> List[Dict[str, Any]]:
    """
    Dense vector search using Pinecone with local in-memory fallback.
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

        if formatted_results:
            return formatted_results

    except Exception as e:
        logger.warning(f"Pinecone vector search not available: {e}")

    # Fallback: Return local chunks
    local = get_all_local_chunks(product_ids)
    return local[:top_k]
