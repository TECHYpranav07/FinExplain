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
    # --- Backward-compatible fields ---
    answer: str
    confidence_score: float
    confidence_label: str
    citations: List[CitationItem] = Field(default_factory=list)
    retrieved_chunks: List[Dict[str, Any]] = Field(default_factory=list)
    intent: Optional[str] = None
    status: Optional[str] = "ok"

    # --- New structured fields ---
    plain_language_explanation: Optional[str] = None
    key_facts: List[Dict[str, Any]] = Field(default_factory=list)
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    calculations: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    missing_information: List[Dict[str, Any]] = Field(default_factory=list)
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_status: Optional[str] = None
    what_to_verify: List[str] = Field(default_factory=list)
    evidence_score: Optional[int] = None
    claim_coverage: Optional[float] = None
    calculation_valid: Optional[bool] = None
    risk_score: Optional[int] = None
    risk_level: Optional[str] = None
    risk_factors: List[Dict[str, Any]] = Field(default_factory=list)
    questions_to_ask_provider: List[str] = Field(default_factory=list)

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

# --- New analysis schemas ---

class LoanReviewRequest(BaseModel):
    product_ids: List[str] = Field(..., description="Product IDs to analyse")

class LoanReviewResponse(BaseModel):
    review: Dict[str, Any] = Field(default_factory=dict)
    review_text: Optional[str] = None
    checklist: Optional[List[Dict[str, Any]]] = None
    cost_drivers: Optional[List[Dict[str, Any]]] = None

class BeforeConfirmationRequest(BaseModel):
    product_ids: List[str] = Field(..., description="Product IDs to analyse")

class BeforeConfirmationResponse(BaseModel):
    checklist: List[Dict[str, Any]] = Field(default_factory=list)
    checklist_text: Optional[str] = None
    summary: Optional[Dict[str, Any]] = None
