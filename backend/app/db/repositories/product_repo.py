from app.db.supabase_client import get_supabase_client
from typing import List, Dict, Any, Optional
import uuid

def create_product(user_id: str, name: str, issuer: str, effective_date: str = None) -> Dict[str, Any]:
    """Create a new product in Supabase."""
    supabase = get_supabase_client()
    
    data = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "name": name,
        "issuer": issuer,
    }
    if effective_date:
        data["effective_date"] = effective_date
    
    response = supabase.table("products").insert(data).execute()
    return response.data[0] if response.data else None

def get_products_by_user(user_id: str) -> List[Dict[str, Any]]:
    """Fetch all products for a given user."""
    supabase = get_supabase_client()
    response = supabase.table("products").select("*").eq("user_id", user_id).execute()
    return response.data or []

def get_all_products(limit: int = 100) -> List[Dict[str, Any]]:
    """Fetch all products."""
    supabase = get_supabase_client()
    response = supabase.table("products").select("*").limit(limit).execute()
    return response.data or []

def get_product_by_id(product_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single product by ID."""
    supabase = get_supabase_client()
    response = supabase.table("products").select("*").eq("id", product_id).execute()
    return response.data[0] if response.data else None

def get_product_by_name(user_id: str, name: str) -> Optional[Dict[str, Any]]:
    """Fetch a product by name for a specific user."""
    supabase = get_supabase_client()
    response = supabase.table("products").select("*").eq("user_id", user_id).eq("name", name).execute()
    return response.data[0] if response.data else None