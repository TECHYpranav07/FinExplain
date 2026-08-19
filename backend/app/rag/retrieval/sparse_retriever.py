from app.db.supabase_client import get_supabase_client
from typing import List, Dict, Any

def bm25_search(query: str, product_ids: List[str], limit: int = 20) -> List[Dict[str, Any]]:
    """
    BM25 full-text search using the PostgreSQL tsvector.
    Calls the RPC function we created earlier: bm25_search_chunks.
    """
    supabase = get_supabase_client()
    
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
        print(f"BM25 search error: {e}")
        # Fallback to direct text search if RPC fails
        # This is a simplified fallback
        query_terms = " & ".join(query.split()[:5])
        response = supabase.table("chunks").select("*")\
            .text_search("search_vector", query_terms)\
            .limit(limit).execute()
        return response.data if response.data else []