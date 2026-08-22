from app.db.supabase_client import get_supabase_client
from typing import Dict, Any, Optional, List
import uuid
import hashlib
import logging

logger = logging.getLogger(__name__)


def compute_product_file_hash(file_hash: str, product_id: str) -> str:
    """Derive a deterministic, product-scoped hash to satisfy DB uniqueness across distinct products."""
    return hashlib.sha256(f"{product_id}:{file_hash}".encode("utf-8")).hexdigest()


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
    scoped_hash = compute_product_file_hash(file_hash, product_id)
    data = {
        "product_id": product_id,
        "file_name": file_name,
        "file_hash": scoped_hash,
        "s3_key": s3_key,
        "total_pages": total_pages,
        "status": status,
    }

    supabase = get_supabase_client()
    try:
        response = supabase.table("documents").insert(data).execute()
        return response.data[0] if response.data else {"id": doc_id, **data}
    except Exception as e:
        logger.warning(f"Insert with scoped hash failed, checking existing: {e}")
        existing = get_document_by_hash(file_hash, product_id)
        if existing:
            return existing
        raise e


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


def get_document_by_hash(file_hash: str, product_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Check if a document already exists for a given product or raw hash in Supabase."""
    supabase = get_supabase_client()
    if product_id:
        scoped_hash = compute_product_file_hash(file_hash, product_id)
        response = (
            supabase.table("documents")
            .select("*")
            .eq("file_hash", scoped_hash)
            .execute()
        )
        if response.data:
            return response.data[0]

    # Fallback to direct raw hash check
    response = (
        supabase.table("documents")
        .select("*")
        .eq("file_hash", file_hash)
        .execute()
    )
    if response.data:
        if product_id:
            # Only match if belongs to the same product
            matched = [d for d in response.data if d.get("product_id") == product_id]
            return matched[0] if matched else None
        return response.data[0]
    return None


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


def get_documents_by_user(user_id: str) -> List[Dict[str, Any]]:
    """Get all documents belonging to products created by a user."""
    supabase = get_supabase_client()
    # First fetch user products
    user_prods = supabase.table("products").select("id, name, issuer").eq("user_id", user_id).execute().data or []
    if not user_prods:
        return []
    
    prod_map = {p["id"]: p for p in user_prods}
    prod_ids = list(prod_map.keys())
    
    docs_res = supabase.table("documents").select("*").in_("product_id", prod_ids).order("upload_date", desc=True).execute()
    docs = docs_res.data or []
    for d in docs:
        p = prod_map.get(d.get("product_id"))
        if p:
            d["product_name"] = p.get("name")
            d["issuer"] = p.get("issuer")
    return docs


def delete_document_by_id(document_id: str) -> bool:
    """Delete a document from Supabase and cascade delete chunks."""
    supabase = get_supabase_client()
    try:
        supabase.table("documents").delete().eq("id", document_id).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {e}")
        return False
