from datetime import datetime, date
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any

class ProductBase(BaseModel):
    name: str
    issuer: str
    effective_date: Optional[date] = None

class ProductCreate(ProductBase):
    user_id: str

class ProductResponse(ProductBase):
    id: str
    user_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
