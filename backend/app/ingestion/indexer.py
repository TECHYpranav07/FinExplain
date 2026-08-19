from typing import List, Dict, Any
from app.db.repositories.chunk_repo import insert_chunks
from app.external.pinecone_client import upsert_vectors

def index_document_chunks(
    chunks: List[Dict[str, Any]],
    embeddings: List[List[float]],
    document_id: str,
    product_id: str
) -> Dict[str, Any]:
    """
    Indexes chunks into Supabase PostgreSQL (for BM25 full-text search)
    and Pinecone (for dense vector search).
    """
    # 1. Prepare vectors for Pinecone
    vectors = []
    for chunk, emb in zip(chunks, embeddings):
        chunk_id = chunk["id"]
        vectors.append({
            "id": chunk_id,
            "values": emb,
            "metadata": {
                "document_id": document_id,
                "product_id": product_id,
                "page_number": chunk.get("page_number", 1),
                "text": chunk.get("text", "")[:1000]  # Store preview in Pinecone
            }
        })
    
    # Upsert vectors into Pinecone
    upsert_vectors(vectors)

    # 2. Insert chunks into Supabase
    db_chunks = []
    for chunk in chunks:
        db_chunks.append({
            "id": chunk["id"],
            "document_id": document_id,
            "parent_id": chunk.get("parent_id"),
            "chunk_index": chunk.get("chunk_index", 0),
            "content": chunk.get("text", ""),
            "page_number": chunk.get("page_number", 1),
            "token_count": len(chunk.get("text", "")) // 4
        })
    
    insert_chunks(db_chunks)

    return {
        "status": "indexed",
        "chunks_indexed": len(chunks),
        "document_id": document_id,
        "product_id": product_id
    }
