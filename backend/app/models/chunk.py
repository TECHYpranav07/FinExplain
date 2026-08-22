from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class ChunkBase(BaseModel):
    id: str
    document_id: str
    parent_chunk_id: Optional[str] = None
    section_name: Optional[str] = None
    text: str
    page_number: Optional[int] = None
    token_count: Optional[int] = None
    embedding_id: Optional[str] = None

class ChunkCreate(ChunkBase):
    pass

class ChunkResponse(ChunkBase):
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
