from app.db.supabase_client import get_supabase_client
from typing import Dict, Any, Optional
import uuid
import logging

logger = logging.getLogger(__name__)

_LOCAL_DOCUMENTS: Dict[str, Dict[str, Any]] = {}

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
    """Create a document using the canonical database schema."""
    doc_id = str(uuid.uuid4())
    # Match the deployed Supabase schema.  File metadata such as version and
    # effective date remains available in the parsed pipeline response until
    # those columns are added through a deliberate database migration.
    data = {
        "product_id": product_id,
        "file_name": file_name,
        "file_hash": file_hash,
        "s3_key": s3_key,
        "total_pages": total_pages,
        "status": status,
    }
    
    try:
        supabase = get_supabase_client()
        response = supabase.table("documents").insert(data).execute()
        return response.data[0] if response.data else {"id": doc_id, **data}
    except Exception as e:
        logger.warning(f"Supabase not available, storing document locally: {e}")
        local_data = {"id": doc_id, "file_name": file_name, **data}
        _LOCAL_DOCUMENTS[doc_id] = local_data
        return local_data

def update_document_status(document_id: str, status: str) -> Dict[str, Any]:
    """Update document processing status."""
    try:
        supabase = get_supabase_client()
        response = supabase.table("documents").update({"status": status}).eq("id", document_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.warning(f"Supabase not available: {e}")
        if document_id in _LOCAL_DOCUMENTS:
            _LOCAL_DOCUMENTS[document_id]["status"] = status
            return _LOCAL_DOCUMENTS[document_id]
        return None

def get_document_by_hash(file_hash: str) -> Optional[Dict[str, Any]]:
    """Check if a document already exists by hash (deduplication)."""
    try:
        supabase = get_supabase_client()
        response = supabase.table("documents").select("*").eq("file_hash", file_hash).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.warning(f"Supabase not available: {e}")
        return next((d for d in _LOCAL_DOCUMENTS.values() if d.get("file_hash") == file_hash), None)

def get_document_by_id(document_id: str) -> Optional[Dict[str, Any]]:
    """Get a document by its ID."""
    try:
        supabase = get_supabase_client()
        response = supabase.table("documents").select("*").eq("id", document_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.warning(f"Supabase not available: {e}")
        return _LOCAL_DOCUMENTS.get(document_id)
