from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class ChunkBase(BaseModel):
    id: str
    document_id: int
    parent_id: Optional[str] = None
    chunk_index: int
    content: str
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    token_count: Optional[int] = None

class ChunkCreate(ChunkBase):
    pass

class ChunkResponse(ChunkBase):
    created_at: datetime

    class Config:
        from_attributes = True