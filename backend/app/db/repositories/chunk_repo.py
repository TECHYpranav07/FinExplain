from app.db.supabase_client import get_supabase_client
from typing import List, Dict, Any
import uuid

def insert_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Insert multiple chunks into Supabase.
    Each chunk should have: document_id, parent_chunk_id (optional), 
    section_name (optional), page_number, text, token_count, embedding_id (optional).
    """
    supabase = get_supabase_client()
    
    # Add UUIDs for each chunk if not present
    for chunk in chunks:
        if "id" not in chunk:
            chunk["id"] = str(uuid.uuid4())
    
    response = supabase.table("chunks").insert(chunks).execute()
    return response.data if response.data else []

def get_chunks_by_document(document_id: str) -> List[Dict[str, Any]]:
    """Retrieve all chunks for a document (for verification)."""
    supabase = get_supabase_client()
    response = supabase.table("chunks").select("*").eq("document_id", document_id).execute()
    return response.data

def bm25_search(query: str, product_ids: List[str], limit: int = 10) -> List[Dict[str, Any]]:
    """
    BM25 full-text search using PostgreSQL tsvector.
    """
    supabase = get_supabase_client()
    
    # Use the RPC function
    try:
        response = supabase.rpc(
            "bm25_search_chunks",
            {
                "query_text": query,
                "product_ids": product_ids,
                "limit_val": limit
            }
        ).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"BM25 RPC error: {e}")
        # Fallback to direct text search
        query_terms = " & ".join(query.split()[:5])
        response = supabase.table("chunks").select("*")\
            .text_search("search_vector", query_terms)\
            .limit(limit).execute()
        return response.data if response.data else []