import hashlib
import uuid
from typing import Dict, Any, Optional
import io

from app.ingestion.parser import parse_pdf
from app.ingestion.chunker import chunk_hierarchical
from app.external.pinecone_client import get_pinecone_index
from app.db.repositories.document_repo import (
    create_document, 
    update_document_status, 
    get_document_by_hash
)
from app.db.repositories.chunk_repo import insert_chunks
from app.db.repositories.product_repo import get_product_by_id

def process_document(
    file_bytes: bytes,
    file_name: str,
    product_id: str,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Full ingestion pipeline:
    1. Check if document already exists (hash deduplication).
    2. Parse PDF (with section heading extraction & metadata detection).
    3. Create hierarchical chunks with rich metadata and user_id.
    4. Generate embeddings.
    5. Store chunks in Supabase.
    6. Upsert vectors to Pinecone (with enriched metadata and user_id).
    7. Update document status to 'indexed'.
    """
    # Loading sentence-transformers is expensive; keep it out of API startup
    # and initialize it only when an upload actually needs embeddings.
    from app.ingestion.embedder import generate_embeddings

    
    # Step 1: Hash the file
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    
    # Check if already processed for this specific product
    existing = get_document_by_hash(file_hash, product_id=product_id)
    if existing:
        return {
            "status": "exists",
            "document_id": existing["id"],
            "message": "Document already indexed for this product."
        }
    
    # Verify product exists
    product = get_product_by_id(product_id)
    if not product:
        raise ValueError(f"Product with ID {product_id} not found.")

    product_name = product.get("name", "")
    resolved_user_id = user_id or product.get("user_id", "")

    # Step 2: Parse PDF (now returns sections and document metadata)
    parsed = parse_pdf(file_bytes)
    full_text = parsed["full_text"]
    pages = parsed["pages"]
    total_pages = parsed["total_pages"]
    doc_metadata = parsed.get("document_metadata", {})
    
    # Step 3: Create document record (status = processing)
    doc = create_document(
        product_id=product_id,
        file_name=file_name,
        file_hash=file_hash,
        s3_key=f"documents/{file_hash}.pdf",  # Simulated S3 key
        total_pages=total_pages,
        status="processing"
    )
    document_id = doc["id"]

    try:
        # Step 4: Chunk hierarchically with enriched metadata (FIN-017: parent_chunk_id assigned)
        raw_chunks = chunk_hierarchical(
            pages,
            child_token_size=200,
            parent_token_size=800,
            document_name=file_name,
            product_name=product_name,
            effective_date=doc_metadata.get("effective_date"),
            document_version=doc_metadata.get("document_version"),
        )
        
        # Separate child and parent chunks for processing
        children = []
        parents = []
        for chunk in raw_chunks:
            if chunk["type"] == "child":
                children.append(chunk)
            else:
                parents.append(chunk)
        
        # Step 5: Generate embeddings for CHILD chunks only (or all chunks)
        child_texts = [c["text"] for c in children]
        child_embeddings = generate_embeddings(child_texts)
        
        # Step 6: Prepare Pinecone vectors with enriched metadata
        pinecone_vectors = []
        for i, child in enumerate(children):
            vector_id = child.get("chunk_id", f"{document_id}_{i}")
            metadata = {
                "document_id": document_id,
                "product_id": product_id,
                "user_id": resolved_user_id,
                "document_name": file_name,
                "product_name": product_name,
                "page_num": child["page_num"],
                "section_title": child.get("section_title") or "",
                "effective_date": doc_metadata.get("effective_date") or "",
                "document_version": doc_metadata.get("document_version") or "",
                "text": child["text"][:500],
                "chunk_type": "child"
            }
            pinecone_vectors.append({
                "id": vector_id,
                "values": child_embeddings[i],
                "metadata": metadata
            })
        
        # Also embed parents if retrievable
        parent_texts = [p["text"] for p in parents]
        parent_embeddings = generate_embeddings(parent_texts)
        
        for i, parent in enumerate(parents):
            vector_id = parent.get("chunk_id", f"{document_id}_parent_{i}")
            metadata = {
                "document_id": document_id,
                "product_id": product_id,
                "user_id": resolved_user_id,
                "document_name": file_name,
                "product_name": product_name,
                "page_num": parent["page_num"],
                "section_title": parent.get("section_title") or "",
                "effective_date": doc_metadata.get("effective_date") or "",
                "document_version": doc_metadata.get("document_version") or "",
                "text": parent["text"][:500],
                "chunk_type": "parent"
            }
            pinecone_vectors.append({
                "id": vector_id,
                "values": parent_embeddings[i],
                "metadata": metadata
            })
        
        # Step 7: Upsert to Pinecone
        try:
            index = get_pinecone_index()
            if index:
                index.upsert(vectors=pinecone_vectors)
        except Exception as e:
            # FIN-011: Log error clearly; in dev mode, we continue to local storage
            import logging
            logging.getLogger(__name__).warning(f"Pinecone upsert skipped: {e}")
        
        # Step 8: Prepare chunks for Supabase insertion (FIN-017: preserve parent_chunk_id)
        db_chunks = []
        
        # Insert child chunks
        for i, child in enumerate(children):
            db_chunks.append({
                "document_id": document_id,
                "parent_chunk_id": child.get("parent_chunk_id"),
                "section_name": child.get("section_title"),
                "page_number": child["page_num"],
                "text": child["text"],
                "token_count": child["token_count"],
                "embedding_id": child.get("chunk_id", f"{document_id}_{i}")
            })
        
        # Insert parent chunks
        for i, parent in enumerate(parents):
            db_chunks.append({
                "document_id": document_id,
                "parent_chunk_id": None,
                "section_name": parent.get("section_title"),
                "page_number": parent["page_num"],
                "text": parent["text"],
                "token_count": parent["token_count"],
                "embedding_id": parent.get("chunk_id", f"{document_id}_parent_{i}")
            })
        
        # Step 9: Insert chunks into Supabase
        inserted_chunks = insert_chunks(db_chunks)
        
        # Step 10: Update document status to 'indexed'
        update_document_status(document_id, "indexed")
        
        return {
            "status": "success",
            "document_id": document_id,
            "total_chunks": len(inserted_chunks),
            "document_metadata": doc_metadata,
            "message": "Document processed and indexed successfully."
        }

    except Exception as e:
        # FIN-013: Update status to 'failed' on error so the document does not remain 'processing'
        import logging
        logging.getLogger(__name__).error(f"Document ingestion failed for {document_id}: {e}")
        try:
            update_document_status(document_id, "failed")
        except Exception:
            pass
        raise e
