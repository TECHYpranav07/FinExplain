import hashlib
import uuid
from typing import Dict, Any
import io

from app.ingestion.parser import parse_pdf
from app.ingestion.chunker import chunk_hierarchical
from app.ingestion.embedder import generate_embeddings
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
    product_id: str
) -> Dict[str, Any]:
    """
    Full ingestion pipeline:
    1. Check if document already exists (hash deduplication).
    2. Parse PDF.
    3. Create hierarchical chunks.
    4. Generate embeddings.
    5. Store chunks in Supabase.
    6. Upsert vectors to Pinecone.
    7. Update document status to 'indexed'.
    """
    
    # Step 1: Hash the file
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    
    # Check if already processed
    existing = get_document_by_hash(file_hash)
    if existing:
        return {
            "status": "exists",
            "document_id": existing["id"],
            "message": "Document already indexed."
        }
    
    # Verify product exists
    product = get_product_by_id(product_id)
    if not product:
        raise ValueError(f"Product with ID {product_id} not found.")
    
    # Step 2: Parse PDF
    parsed = parse_pdf(file_bytes)
    full_text = parsed["full_text"]
    pages = parsed["pages"]
    total_pages = parsed["total_pages"]
    
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
    
    # Step 4: Chunk hierarchically
    raw_chunks = chunk_hierarchical(pages, child_token_size=200, parent_token_size=800)
    
    # Separate child and parent chunks for processing
    children = []
    parents = []
    for chunk in raw_chunks:
        if chunk["type"] == "child":
            children.append(chunk)
        else:
            parents.append(chunk)
    
    # Step 5: Generate embeddings for CHILD chunks only (or all chunks)
    # We embed children for high-precision retrieval
    child_texts = [c["text"] for c in children]
    child_embeddings = generate_embeddings(child_texts)
    
    # Step 6: Prepare Pinecone vectors
    pinecone_vectors = []
    for i, child in enumerate(children):
        vector_id = f"{document_id}_{i}"
        metadata = {
            "document_id": document_id,
            "product_id": product_id,
            "page_num": child["page_num"],
            "text": child["text"][:500],  # Pinecone metadata limit
            "chunk_type": "child"
        }
        pinecone_vectors.append({
            "id": vector_id,
            "values": child_embeddings[i],
            "metadata": metadata
        })
    
    # Also embed parents if you want them retrievable
    parent_texts = [p["text"] for p in parents]
    parent_embeddings = generate_embeddings(parent_texts)
    
    for i, parent in enumerate(parents):
        vector_id = f"{document_id}_parent_{i}"
        metadata = {
            "document_id": document_id,
            "product_id": product_id,
            "page_num": parent["page_num"],
            "text": parent["text"][:500],
            "chunk_type": "parent"
        }
        pinecone_vectors.append({
            "id": vector_id,
            "values": parent_embeddings[i],
            "metadata": metadata
        })
    
    # Step 7: Upsert to Pinecone
    index = get_pinecone_index()
    index.upsert(vectors=pinecone_vectors)
    
    # Step 8: Prepare chunks for Supabase insertion
    db_chunks = []
    
    # Insert child chunks
    for i, child in enumerate(children):
        db_chunks.append({
            "document_id": document_id,
            "parent_chunk_id": None,  # Will link after parents are inserted
            "section_name": None,
            "page_number": child["page_num"],
            "text": child["text"],
            "token_count": child["token_count"],
            "embedding_id": f"{document_id}_{i}"
        })
    
    # Insert parent chunks
    for i, parent in enumerate(parents):
        db_chunks.append({
            "document_id": document_id,
            "parent_chunk_id": None,
            "section_name": None,
            "page_number": parent["page_num"],
            "text": parent["text"],
            "token_count": parent["token_count"],
            "embedding_id": f"{document_id}_parent_{i}"
        })
    
    # Step 9: Insert chunks into Supabase
    inserted_chunks = insert_chunks(db_chunks)
    
    # Step 10: Update document status to 'indexed'
    update_document_status(document_id, "indexed")
    
    return {
        "status": "success",
        "document_id": document_id,
        "total_chunks": len(inserted_chunks),
        "message": "Document processed and indexed successfully."
    }