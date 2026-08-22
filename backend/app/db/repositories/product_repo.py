from app.db.supabase_client import get_supabase_client
from typing import List, Dict, Any, Optional
import uuid
import logging
from datetime import date

logger = logging.getLogger(__name__)


def create_product(
    user_id: str,
    name: str,
    issuer: str,
    effective_date: str = None,
    product_type: str = "loan",
) -> Dict[str, Any]:
    """Create a product in the Supabase cloud PostgreSQL database."""
    pid = str(uuid.uuid4())
    data = {
        "name": name,
        "issuer": issuer,
        "user_id": user_id,
        "effective_date": effective_date or date.today().isoformat(),
    }

    supabase = get_supabase_client()
    response = supabase.table("products").insert(data).execute()
    return response.data[0] if response.data else {"id": pid, **data}


def get_products_by_user(user_id: str) -> List[Dict[str, Any]]:
    """Fetch all products for a given user from Supabase cloud database."""
    supabase = get_supabase_client()
    response = supabase.table("products").select("*").eq("user_id", user_id).execute()
    return response.data or []


def get_all_products(limit: int = 100) -> List[Dict[str, Any]]:
    """Fetch all products from Supabase cloud database."""
    supabase = get_supabase_client()
    response = supabase.table("products").select("*").limit(limit).execute()
    return response.data or []


def get_product_by_id(product_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single product by ID from Supabase cloud database."""
    supabase = get_supabase_client()
    response = supabase.table("products").select("*").eq("id", product_id).execute()
    if response.data:
        return response.data[0]
    return None


def get_product_by_name(user_id: str, name: str) -> Optional[Dict[str, Any]]:
    """Fetch a product by name for a specific user from Supabase cloud database."""
    supabase = get_supabase_client()
    response = (
        supabase.table("products")
        .select("*")
        .eq("user_id", user_id)
        .eq("name", name)
        .execute()
    )
    return response.data[0] if response.data else None
