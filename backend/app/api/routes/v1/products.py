from fastapi import APIRouter
from typing import Dict, Any, List

router = APIRouter()

@router.get("/")
async def list_products() -> List[Dict[str, Any]]:
    return [{"id": 1, "name": "Standard Home Loan", "issuer": "Bank A"}]

@router.get("/{product_id}")
async def get_product(product_id: int) -> Dict[str, Any]:
    return {"id": product_id, "name": "Standard Home Loan", "issuer": "Bank A"}
