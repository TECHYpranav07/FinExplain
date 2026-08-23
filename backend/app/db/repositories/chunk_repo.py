from app.db.supabase_client import get_supabase_client
from typing import List, Dict, Any, Optional
import uuid
import logging
import re
import math

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


def get_chunks_by_ids(chunk_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Batch fetch chunks by their IDs from Supabase for parent context expansion."""
    if not chunk_ids:
        return {}
    try:
        supabase = get_supabase_client()
        clean_ids = [str(cid) for cid in set(chunk_ids) if cid]
        response = supabase.table("chunks").select("*").in_("id", clean_ids).execute()
        return {r["id"]: r for r in (response.data or []) if r.get("id")}
    except Exception as e:
        logger.debug(f"Failed to fetch chunks by ids: {e}")
        return {}


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
            
            # Full-text candidate retrieval with BM25 / TF-IDF rank scoring
            remote_chunks = chunk_query.limit(limit * 8).execute().data or []
            if not remote_chunks:
                return []

            # 1. Tokenize query and remove common stopwords
            stop_words = {
                "what", "is", "the", "a", "an", "of", "in", "for", "and", "or",
                "to", "on", "at", "by", "my", "me", "i", "how", "much", "this",
                "that", "are", "was", "be", "do", "does", "did", "will", "would",
                "can", "could", "if", "there", "with", "from", "about", "any", "please",
                "tell", "give", "show", "check", "loan", "under", "per", "agreement"
            }
            raw_query_words = [w.lower() for w in re.findall(r'\w+', query) if len(w) > 1]
            query_terms = [w for w in raw_query_words if w not in stop_words] or raw_query_words

            if not query_terms:
                return remote_chunks[:limit]

            # 2. Compute document frequencies (DF) for IDF calculation
            num_docs = len(remote_chunks)
            doc_token_lists = []
            doc_lengths = []
            term_doc_counts = {term: 0 for term in query_terms}

            for chunk in remote_chunks:
                text = (chunk.get("text") or "").lower()
                tokens = re.findall(r'\w+', text)
                doc_token_lists.append(tokens)
                doc_lengths.append(len(tokens))
                token_set = set(tokens)
                for term in query_terms:
                    if term in token_set:
                        term_doc_counts[term] += 1

            avg_dl = sum(doc_lengths) / max(num_docs, 1) or 1.0
            k1 = 1.5
            b = 0.75

            # 3. Score each chunk using BM25 formula + financial signal bonus
            scored = []
            for i, chunk in enumerate(remote_chunks):
                tokens = doc_token_lists[i]
                doc_len = doc_lengths[i]
                tf_counts = {}
                for t in tokens:
                    tf_counts[t] = tf_counts.get(t, 0) + 1

                score = 0.0
                for term in query_terms:
                    tf = tf_counts.get(term, 0)
                    if tf == 0:
                        continue
                    df = term_doc_counts[term]
                    idf = math.log(1.0 + (num_docs - df + 0.5) / (df + 0.5))
                    bm25_term = idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (doc_len / avg_dl)))
                    score += bm25_term

                if score > 0:
                    # Boost table chunks and chunks with financial values
                    text_raw = chunk.get("text", "")
                    if re.search(r'[\d%₹$]|(?:percent|fee|charge|rate|p\.a\.|annual|schedule)', text_raw, re.I):
                        score *= 1.2
                    chunk["bm25_score"] = float(score)
                    scored.append((score, chunk))

            scored.sort(key=lambda item: item[0], reverse=True)
            return [item[1] for item in scored[:limit]]
    except Exception as e:
        logger.error(f"Supabase chunks query failed: {e}")

    return []
