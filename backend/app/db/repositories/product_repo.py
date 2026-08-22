from app.db.supabase_client import get_supabase_client
from app.core.config import settings
from typing import List, Dict, Any, Optional
import uuid
import logging
from datetime import date

logger = logging.getLogger(__name__)

# Fallback local store for demo / local testing when Supabase credentials are not set
_LOCAL_PRODUCTS: Dict[str, Dict[str, Any]] = {
    "1": {"id": "1", "name": "Sample Home Loan A", "issuer": "HDFC Bank", "effective_date": "2025-01-01"},
    "2": {"id": "2", "name": "Sample Personal Loan B", "issuer": "SBI Bank", "effective_date": "2025-02-01"},
}

def create_product(
    user_id: str,
    name: str,
    issuer: str,
    effective_date: str = None,
    product_type: str = "loan",
) -> Dict[str, Any]:
    """Create a product using the column names and types in ``schema.sql``."""
    pid = str(uuid.uuid4())
    data = {
        "name": name,
        "issuer": issuer,
        "user_id": user_id,
    }
    data["effective_date"] = effective_date or date.today().isoformat()
    
    try:
        supabase = get_supabase_client()
        response = supabase.table("products").insert(data).execute()
        return response.data[0] if response.data else {"id": pid, **data}
    except Exception as e:
        logger.warning(f"Supabase not available, using local product store: {e}")
        if settings.is_development:
            local_data = {"id": pid, **data}
            _LOCAL_PRODUCTS[pid] = local_data
            return local_data
        raise e

def get_products_by_user(user_id: str) -> List[Dict[str, Any]]:
    """Fetch all products for a given user."""
    try:
        supabase = get_supabase_client()
        response = supabase.table("products").select("*").eq("user_id", user_id).execute()
        return response.data or []
    except Exception as e:
        logger.warning(f"Supabase not available: {e}")
        return list(_LOCAL_PRODUCTS.values()) if settings.is_development else []

def get_all_products(limit: int = 100) -> List[Dict[str, Any]]:
    """Fetch all products."""
    try:
        supabase = get_supabase_client()
        response = supabase.table("products").select("*").limit(limit).execute()
        return response.data or []
    except Exception as e:
        logger.warning(f"Supabase not available: {e}")
        return list(_LOCAL_PRODUCTS.values()) if settings.is_development else []

def get_product_by_id(product_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single product by ID."""
    try:
        supabase = get_supabase_client()
        response = supabase.table("products").select("*").eq("id", product_id).execute()
        if response.data:
            return response.data[0]
    except Exception as e:
        logger.warning(f"Supabase not available, checking local store: {e}")
    
    if settings.is_development:
        return _LOCAL_PRODUCTS.get(product_id)
    return None

def get_product_by_name(user_id: str, name: str) -> Optional[Dict[str, Any]]:
    """Fetch a product by name for a specific user."""
    try:
        supabase = get_supabase_client()
        response = supabase.table("products").select("*").eq("user_id", user_id).eq("name", name).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.warning(f"Supabase not available: {e}")
        if settings.is_development:
            return next((p for p in _LOCAL_PRODUCTS.values() if p.get("name") == name), None)
        return None
