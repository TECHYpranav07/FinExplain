from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class DocumentBase(BaseModel):
    filename: str
    file_hash: str
    s3_key: Optional[str] = None
    file_size: int
    total_pages: int = 0
    status: str = "uploaded"
    product_id: Optional[int] = None

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(DocumentBase):
    id: int
    uploaded_at: datetime

    class Config:
        from_attributes = True