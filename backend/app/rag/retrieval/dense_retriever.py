from app.external.pinecone_client import get_pinecone_index
from app.ingestion.embedder import generate_embedding
from typing import List, Dict, Any

def vector_search(query: str, product_ids: List[str], top_k: int = 20) -> List[Dict[str, Any]]:
    """
    Dense vector search using Pinecone.
    Filters by product_id metadata.
    """
    index = get_pinecone_index()
    
    # Generate embedding for the query
    query_vector = generate_embedding(query)
    
    # Prepare metadata filter
    filter_dict = {"product_id": {"$in": product_ids}} if product_ids else {}
    
    # Query Pinecone
    results = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True,
        filter=filter_dict
    )
    
    # Format results to match BM25 output structure
    formatted_results = []
    for match in results.matches:
        formatted_results.append({
            "id": match.id,
            "document_id": match.metadata.get("document_id"),
            "product_id": match.metadata.get("product_id"),
            "page_number": match.metadata.get("page_num"),
            "text": match.metadata.get("text", ""),
            "embedding_id": match.id,
            "score": match.score,  # Similarity score
            "rank": match.rank if hasattr(match, 'rank') else None,
            "chunk_type": match.metadata.get("chunk_type", "child")
        })
    
    return formatted_results