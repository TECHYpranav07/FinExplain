from typing import List, Dict, Any
from app.db.repositories.chunk_repo import bm25_search as repo_bm25_search

def bm25_search(query: str, product_ids: List[str], limit: int = 20) -> List[Dict[str, Any]]:
    """
    BM25 full-text search with Supabase RPC and local keyword fallback.
    """
    return repo_bm25_search(query=query, product_ids=product_ids, limit=limit)