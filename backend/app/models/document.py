from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class DocumentBase(BaseModel):
    file_name: str
    file_hash: str
    s3_key: Optional[str] = None
    total_pages: int = 0
    status: str = "uploaded"
    product_id: Optional[str] = None

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(DocumentBase):
    id: str
    upload_date: datetime

    model_config = ConfigDict(from_attributes=True)
