from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, List

class VerifiedAnswerBase(BaseModel):
    user_query: str
    context_hash: Optional[str] = None
    final_answer: str
    source_citations: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_score: Optional[float] = None
    verified_by_user_id: Optional[str] = None

class VerifiedAnswerCreate(VerifiedAnswerBase):
    pass

class VerifiedAnswerResponse(VerifiedAnswerBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
