from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class VerifiedAnswerBase(BaseModel):
    user_query: str
    context_hash: Optional[str] = None
    final_answer: str
    source_citations: List[Dict[str, Any]] = []
    confidence_score: Optional[float] = None
    verified_by_user_id: Optional[int] = None

class VerifiedAnswerCreate(VerifiedAnswerBase):
    pass

class VerifiedAnswerResponse(VerifiedAnswerBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True