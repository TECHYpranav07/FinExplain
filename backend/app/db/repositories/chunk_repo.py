from app.db.supabase_client import get_supabase_client
from typing import List, Dict, Any, Optional
import uuid
import logging

logger = logging.getLogger(__name__)


def insert_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Insert multiple chunks into the Supabase cloud database.
    """
    normalized_chunks = []
    for index, chunk in enumerate(chunks):
        chunk_id = (
            chunk.get("id")
            or chunk.get("chunk_id")
            or chunk.get("embedding_id")
            or str(uuid.uuid4())
        )
        normalized_chunks.append({
            "id": chunk_id,
            "document_id": chunk.get("document_id"),
            "parent_chunk_id": chunk.get("parent_chunk_id"),
            "section_name": chunk.get("section_name", chunk.get("section_title")),
            "page_number": chunk.get("page_number", chunk.get("page_num")),
            "text": chunk.get("text", chunk.get("content", "")),
            "token_count": chunk.get("token_count"),
            "embedding_id": chunk.get("embedding_id", chunk_id),
        })

    supabase = get_supabase_client()
    response = supabase.table("chunks").insert(normalized_chunks).execute()
    return response.data if response.data else normalized_chunks


def get_chunks_by_document(document_id: str) -> List[Dict[str, Any]]:
    """Retrieve all chunks for a document from Supabase cloud database."""
    supabase = get_supabase_client()
    response = supabase.table("chunks").select("*").eq("document_id", document_id).execute()
    return response.data or []


def bm25_search(query: str, product_ids: List[str], limit: int = 10) -> List[Dict[str, Any]]:
    """
    BM25 / Full-Text search executed on Supabase cloud PostgreSQL.
    Uses bm25_search_chunks RPC or search_vector full-text query.
    """
    supabase = get_supabase_client()

    # Attempt 1: Call Supabase bm25_search_chunks RPC if created
    try:
        response = supabase.rpc(
            "bm25_search_chunks",
            {
                "query_text": query,
                "product_ids": product_ids,
                "limit_val": limit,
            },
        ).execute()
        if response.data:
            return response.data
    except Exception as e:
        logger.info(f"Supabase RPC bm25_search_chunks fallback to standard table query: {e}")

    # Attempt 2: Standard Supabase table full-text query on chunks joined with documents
    try:
        doc_query = supabase.table("documents").select("id")
        if product_ids:
            doc_query = doc_query.in_("product_id", product_ids)
        doc_rows = doc_query.execute().data or []
        doc_ids = [r["id"] for r in doc_rows if r.get("id")]

        if doc_ids or not product_ids:
            chunk_query = supabase.table("chunks").select("*")
            if doc_ids:
                chunk_query = chunk_query.in_("document_id", doc_ids)
            
            # Use PostgreSQL text search on search_vector
            remote_chunks = chunk_query.limit(limit * 5).execute().data or []
            query_words = set(query.lower().split())
            scored = []
            for chunk in remote_chunks:
                text = (chunk.get("text") or "").lower()
                chunk_words = set(text.split())
                overlap = len(query_words & chunk_words)
                if overlap > 0:
                    scored.append((overlap, chunk))
            scored.sort(key=lambda item: item[0], reverse=True)
            return [item[1] for item in scored[:limit]]
    except Exception as e:
        logger.error(f"Supabase chunks query failed: {e}")

    return []
