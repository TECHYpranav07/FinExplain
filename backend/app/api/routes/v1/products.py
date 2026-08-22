from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.db.repositories import product_repo
from app.auth.jwt_handler import get_current_user
from app.core.config import settings

router = APIRouter()


class CreateProductRequest(BaseModel):
    name: str
    issuer: str
    effective_date: Optional[str] = None


@router.post("/")
async def create_product(
    request: CreateProductRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a new financial product isolated to the authenticated user."""
    user_id = current_user["id"]
    product = product_repo.create_product(
        user_id=user_id,
        name=request.name,
        issuer=request.issuer,
        effective_date=request.effective_date,
    )
    if not product:
        raise HTTPException(status_code=500, detail="Failed to create product")
    return product


@router.get("/")
async def list_products(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """List only products belonging to the authenticated user."""
    user_id = current_user["id"]
    products = product_repo.get_products_by_user(user_id=user_id)
    return products


@router.get("/{product_id}")
async def get_product(
    product_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get a product by its ID, ensuring it belongs to the authenticated user."""
    product = product_repo.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # In development mode, allow built-in sample products (1 and 2) for demo/testing
    if product_id in ("1", "2") and settings.is_development:
        return product

    if product.get("user_id") and product.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied to this product")

    return product

