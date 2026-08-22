from app.db.supabase_client import get_supabase_client
from typing import List, Dict, Any, Optional
import uuid
import os
import logging

logger = logging.getLogger(__name__)

_LOCAL_CHUNKS: List[Dict[str, Any]] = []

def _ensure_sample_loan_chunks():
    """Pre-load sample loan PDF chunks for Product 1 if no chunks are loaded yet."""
    global _LOCAL_CHUNKS
    if _LOCAL_CHUNKS:
        return

    # Check root workspace and backend directories for sample_loan_details.pdf
    repo_dir = os.path.dirname(__file__)
    candidate_paths = [
        os.path.abspath(os.path.join(repo_dir, "..", "..", "..", "..", "sample_loan_details.pdf")),
        os.path.abspath(os.path.join(repo_dir, "..", "..", "..", "sample_loan_details.pdf")),
        os.path.abspath("sample_loan_details.pdf"),
        os.path.abspath("../sample_loan_details.pdf"),
    ]

    sample_pdf_path = next((p for p in candidate_paths if os.path.exists(p)), None)

    if sample_pdf_path:
        try:
            from app.ingestion.parser import parse_pdf
            from app.ingestion.chunker import chunk_hierarchical
            with open(sample_pdf_path, "rb") as f:
                file_bytes = f.read()
            parsed = parse_pdf(file_bytes)
            chunks = chunk_hierarchical(
                parsed["pages"],
                child_token_size=200,
                parent_token_size=800,
                document_name="sample_loan_details.pdf",
                product_name="Sample Personal Loan A",
                effective_date="2026-08-15",
                document_version="1.0"
            )
            for c in chunks:
                c["id"] = c.get("chunk_id", str(uuid.uuid4()))
                c["product_id"] = "1"
                c["document_id"] = "sample_doc_1"
                c["page_number"] = c.get("page_num", 1)
            _LOCAL_CHUNKS.extend(chunks)
            logger.info(f"Loaded {len(chunks)} local fallback chunks from sample_loan_details.pdf")
        except Exception as e:
            logger.warning(f"Could not preload sample PDF chunks: {e}")

# Preload on import
_ensure_sample_loan_chunks()

def insert_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Insert multiple chunks into Supabase (with local fallback).
    """
    global _LOCAL_CHUNKS
    normalized_chunks = []
    for index, chunk in enumerate(chunks):
        # Use the Pinecone/ingestion id as the database id.  Generating a new
        # id here would make dense and sparse results impossible to fuse.
        chunk_id = (
            chunk.get("id")
            or chunk.get("chunk_id")
            or chunk.get("embedding_id")
            or str(uuid.uuid4())
        )
        local_chunk = dict(chunk)
        local_chunk["id"] = chunk_id
        local_chunk.setdefault("chunk_index", index)
        local_chunk.setdefault("text", local_chunk.get("content", ""))
        local_chunk.setdefault("page_number", local_chunk.get("page_num"))
        _LOCAL_CHUNKS[:] = [c for c in _LOCAL_CHUNKS if c.get("id") != chunk_id]
        _LOCAL_CHUNKS.append(local_chunk)
        normalized_chunks.append({
            "id": chunk_id,
            "document_id": chunk.get("document_id"),
            "parent_chunk_id": chunk.get("parent_chunk_id"),
            "section_name": chunk.get("section_name", chunk.get("section_title")),
            "page_number": chunk.get("page_number", chunk.get("page_num")),
            "text": chunk.get("text", chunk.get("content", "")),
            "token_count": chunk.get("token_count"),
            "embedding_id": local_chunk.get("embedding_id", chunk_id),
        })

    try:
        supabase = get_supabase_client()
        response = supabase.table("chunks").insert(normalized_chunks).execute()
        return response.data if response.data else normalized_chunks
    except Exception as e:
        logger.warning(f"Supabase not available, saved chunks locally: {e}")
        return normalized_chunks

def get_chunks_by_document(document_id: str) -> List[Dict[str, Any]]:
    """Retrieve all chunks for a document."""
    try:
        supabase = get_supabase_client()
        response = supabase.table("chunks").select("*").eq("document_id", document_id).execute()
        return response.data or []
    except Exception as e:
        logger.warning(f"Supabase not available: {e}")
        return [c for c in _LOCAL_CHUNKS if c.get("document_id") == document_id]

def get_all_local_chunks(product_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Retrieve all in-memory chunks, optionally filtered by product_ids."""
    from app.core.config import settings
    if not settings.is_development:
        return []
    _ensure_sample_loan_chunks()
    if not product_ids:
        return list(_LOCAL_CHUNKS)
    str_pids = [str(p) for p in product_ids]
    return [c for c in _LOCAL_CHUNKS if str(c.get("product_id")) in str_pids]

def bm25_search(query: str, product_ids: List[str], limit: int = 10) -> List[Dict[str, Any]]:
    """
    BM25 / Keyword search with local fallback.
    """
    from app.core.config import settings
    try:
        supabase = get_supabase_client()
        response = supabase.rpc(
            "bm25_search_chunks",
            {
                "query_text": query,
                "product_ids": product_ids,
                "limit_val": limit
            }
        ).execute()
        if response.data:
            return response.data
    except Exception as e:
        logger.warning(f"Supabase BM25 not available, using local text search: {e}")

        # Older deployments may not have the BM25 RPC yet. Search the live
        # chunks table before falling back to the in-memory sample data.
        try:
            supabase = get_supabase_client()
            document_query = supabase.table("documents").select("id")
            if product_ids:
                document_query = document_query.in_("product_id", product_ids)
            document_rows = document_query.execute().data or []
            document_ids = [row["id"] for row in document_rows if row.get("id")]
            if document_ids or not product_ids:
                chunk_query = supabase.table("chunks").select("*")
                if document_ids:
                    chunk_query = chunk_query.in_("document_id", document_ids)
                remote_chunks = chunk_query.limit(limit * 5).execute().data or []
                query_words = set(query.lower().split())
                scored_remote = []
                for chunk in remote_chunks:
                    text = (chunk.get("text") or "").lower()
                    chunk_words = set(text.split())
                    overlap = len(query_words & chunk_words)
                    if overlap:
                        scored_remote.append((overlap, chunk))
                scored_remote.sort(key=lambda item: item[0], reverse=True)
                if scored_remote:
                    return [item[1] for item in scored_remote[:limit]]
        except Exception as remote_error:
            logger.warning(f"Remote chunk fallback unavailable: {remote_error}")

    # Local fallback keyword search — only in development mode (FIN-034)
    if not settings.is_development:
        return []

    _ensure_sample_loan_chunks()
    chunks = get_all_local_chunks(product_ids)
    query_words = set(query.lower().split())

    scored = []
    for c in chunks:
        text = (c.get("text") or c.get("content") or "").lower()
        chunk_words = set(text.split())
        overlap = len(query_words & chunk_words)
        if overlap > 0 or len(chunks) <= limit:
            scored.append((overlap, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:limit]]
