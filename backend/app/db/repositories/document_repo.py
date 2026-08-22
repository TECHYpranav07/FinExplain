from app.db.supabase_client import get_supabase_client
from typing import Dict, Any, Optional, List
import uuid
import logging

logger = logging.getLogger(__name__)


def create_document(
    product_id: str,
    file_name: str,
    file_hash: str,
    s3_key: str,
    total_pages: int,
    status: str = "processing",
    file_size: int = 0,
    document_version: Optional[str] = None,
    effective_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a document record in the Supabase cloud database."""
    doc_id = str(uuid.uuid4())
    data = {
        "product_id": product_id,
        "file_name": file_name,
        "file_hash": file_hash,
        "s3_key": s3_key,
        "total_pages": total_pages,
        "status": status,
    }

    supabase = get_supabase_client()
    response = supabase.table("documents").insert(data).execute()
    return response.data[0] if response.data else {"id": doc_id, **data}


def update_document_status(document_id: str, status: str) -> Optional[Dict[str, Any]]:
    """Update document processing status in Supabase cloud database."""
    supabase = get_supabase_client()
    response = (
        supabase.table("documents")
        .update({"status": status})
        .eq("id", document_id)
        .execute()
    )
    return response.data[0] if response.data else None


def get_document_by_hash(file_hash: str) -> Optional[Dict[str, Any]]:
    """Check if a document already exists by hash in Supabase cloud database."""
    supabase = get_supabase_client()
    response = (
        supabase.table("documents")
        .select("*")
        .eq("file_hash", file_hash)
        .execute()
    )
    return response.data[0] if response.data else None


def get_document_by_id(document_id: str) -> Optional[Dict[str, Any]]:
    """Get a document by its ID from Supabase cloud database."""
    supabase = get_supabase_client()
    response = supabase.table("documents").select("*").eq("id", document_id).execute()
    return response.data[0] if response.data else None


def get_documents_by_product(product_id: str) -> List[Dict[str, Any]]:
    """Get all documents for a product from Supabase cloud database."""
    supabase = get_supabase_client()
    response = (
        supabase.table("documents")
        .select("*")
        .eq("product_id", product_id)
        .execute()
    )
    return response.data or []
