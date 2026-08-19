from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ProductCreateRequest(BaseModel):
    name: str
    issuer: str
    effective_date: Optional[str] = None

class ProductResponse(BaseModel):
    id: str
    name: str
    issuer: str
    effective_date: Optional[str] = None
    created_at: Optional[datetime] = None

class QueryAskRequest(BaseModel):
    question: str
    product_ids: List[str] = Field(default_factory=list)

class CitationItem(BaseModel):
    page: Optional[int] = None
    section: Optional[str] = None
    verified: bool = False

class QueryAskResponse(BaseModel):
    answer: str
    confidence_score: float
    confidence_label: str
    citations: List[CitationItem] = Field(default_factory=list)
    retrieved_chunks: List[Dict[str, Any]] = Field(default_factory=list)
    intent: Optional[str] = None
    status: Optional[str] = "ok"

class FeedbackSubmitRequest(BaseModel):
    query: str
    answer: str
    is_correct: bool
    correction: Optional[str] = None

class HILTTaskCreateRequest(BaseModel):
    task_type: str
    payload: Dict[str, Any]

class HILTTaskResolveRequest(BaseModel):
    resolution_data: Dict[str, Any]
