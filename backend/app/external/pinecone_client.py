from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Any, Optional
from app.core.config import settings

_pinecone_client: Pinecone | None = None
_pinecone_index = None

def get_pinecone_client() -> Pinecone:
    global _pinecone_client
    if _pinecone_client is None:
        if not settings.PINECONE_API_KEY:
            raise ValueError("PINECONE_API_KEY is not configured in settings.")
        _pinecone_client = Pinecone(api_key=settings.PINECONE_API_KEY)
    return _pinecone_client

def get_pinecone_index():
    global _pinecone_index
    if _pinecone_index is None:
        pc = get_pinecone_client()
        index_name = settings.PINECONE_INDEX_NAME
        
        # Check if index exists, create if not present
        existing_indexes = [idx.name for idx in pc.list_indexes()]
        if index_name not in existing_indexes:
            pc.create_index(
                name=index_name,
                dimension=384,  # Default for all-MiniLM-L6-v2 embeddings
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
        _pinecone_index = pc.Index(index_name)
    return _pinecone_index

def upsert_vectors(vectors: List[Dict[str, Any]], namespace: str = ""):
    """
    Upsert vectors to Pinecone index.
    vectors format: [{"id": "vec1", "values": [0.1, ...], "metadata": {"doc_id": 1, ...}}]
    """
    index = get_pinecone_index()
    return index.upsert(vectors=vectors, namespace=namespace)

def query_vectors(
    query_vector: List[float],
    top_k: int = 10,
    filter_dict: Optional[Dict[str, Any]] = None,
    namespace: str = ""
) -> List[Dict[str, Any]]:
    """
    Query Pinecone for top_k nearest neighbors with metadata filtering.
    """
    index = get_pinecone_index()
    results = index.query(
        vector=query_vector,
        top_k=top_k,
        filter=filter_dict,
        include_metadata=True,
        namespace=namespace
    )
    return results.to_dict().get("matches", [])

def delete_vectors(ids: List[str], namespace: str = ""):
    """
    Delete vectors by IDs from Pinecone.
    """
    index = get_pinecone_index()
    index.delete(ids=ids, namespace=namespace)
