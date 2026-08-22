from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.db.repositories import product_repo
import uuid
from app.core.constants import DEFAULT_DEMO_USER_ID

router = APIRouter()

# Default test user ID (UUID format to match Supabase schema)
# This is the test user already in Supabase (created manually)
DEFAULT_USER_ID = DEFAULT_DEMO_USER_ID

class CreateProductRequest(BaseModel):
    name: str
    issuer: str
    effective_date: Optional[str] = None

@router.post("/")
async def create_product(request: CreateProductRequest) -> Dict[str, Any]:
    """Create a new financial product."""
    product = product_repo.create_product(
        user_id=DEFAULT_USER_ID,
        name=request.name,
        issuer=request.issuer,
        effective_date=request.effective_date
    )
    if not product:
        raise HTTPException(status_code=500, detail="Failed to create product")
    return product

@router.get("/")
async def list_products() -> List[Dict[str, Any]]:
    """List all products."""
    products = product_repo.get_all_products()
    return products

@router.get("/{product_id}")
async def get_product(product_id: str) -> Dict[str, Any]:
    """Get a product by its ID."""
    product = product_repo.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
