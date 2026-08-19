from datetime import datetime, date
from pydantic import BaseModel
from typing import Optional, Dict, Any

class ProductBase(BaseModel):
    name: str
    issuer: str
    product_type: str
    effective_date: Optional[date] = None
    metadata: Dict[str, Any] = {}

class ProductCreate(ProductBase):
    owner_id: int

class ProductResponse(ProductBase):
    id: int
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True