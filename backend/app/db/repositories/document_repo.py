from app.db.supabase_client import get_supabase_client
from typing import Dict, Any, Optional
import uuid
from datetime import datetime

def create_document(
    product_id: str,
    file_name: str,
    file_hash: str,
    s3_key: str,
    total_pages: int,
    status: str = "processing"
) -> Dict[str, Any]:
    """Create a document record in Supabase."""
    supabase = get_supabase_client()
    
    data = {
        "id": str(uuid.uuid4()),
        "product_id": product_id,
        "file_name": file_name,
        "file_hash": file_hash,
        "s3_key": s3_key,
        "total_pages": total_pages,
        "status": status,
        "upload_date": datetime.utcnow().isoformat()
    }
    
    response = supabase.table("documents").insert(data).execute()
    return response.data[0] if response.data else None

def update_document_status(document_id: str, status: str) -> Dict[str, Any]:
    """Update document processing status."""
    supabase = get_supabase_client()
    response = supabase.table("documents").update({"status": status}).eq("id", document_id).execute()
    return response.data[0] if response.data else None

def get_document_by_hash(file_hash: str) -> Optional[Dict[str, Any]]:
    """Check if a document already exists by hash (deduplication)."""
    supabase = get_supabase_client()
    response = supabase.table("documents").select("*").eq("file_hash", file_hash).execute()
    return response.data[0] if response.data else None

def get_document_by_id(document_id: str) -> Optional[Dict[str, Any]]:
    """Get a document by its ID."""
    supabase = get_supabase_client()
    response = supabase.table("documents").select("*").eq("id", document_id).execute()
    return response.data[0] if response.data else None