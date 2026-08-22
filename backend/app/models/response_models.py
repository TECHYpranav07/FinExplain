"""
Structured response models for the FinExplain evidence-first pipeline.

These Pydantic models define the rich structured output that the
frontend can render, while keeping backward compatibility with the
existing ``answer`` + ``confidence_score`` + ``citations`` contract.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.core.loan_categories import EvidenceStatus


class EvidenceItem(BaseModel):
    """A single evidence reference attached to a claim."""

    claim: str = ""
    document: Optional[str] = None
    page: Optional[int] = None
    section: Optional[str] = None
    chunk_id: Optional[str] = None
    status: EvidenceStatus = EvidenceStatus.NOT_SPECIFIED
    verified: bool = False


class CalculationDetail(BaseModel):
    """A transparent calculation result block."""

    type: str = ""
    inputs: Dict[str, Any] = Field(default_factory=dict)
    formula: str = ""
    result: Optional[Any] = None
    unknown_inputs: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)


class StructuredResponse(BaseModel):
    """
    Full structured response from the evidence-first pipeline.

    The ``answer`` field is always present for backward compatibility.
    """

    # --- Backward-compatible fields ---
    answer: str = ""
    confidence_score: float = 0.0
    confidence_label: str = "Low"
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    intent: Optional[str] = None
    status: Optional[str] = "ok"

    # --- New structured fields ---
    plain_language_explanation: Optional[str] = None
    key_facts: List[Dict[str, Any]] = Field(default_factory=list)
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    calculations: List[CalculationDetail] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    missing_information: List[Dict[str, Any]] = Field(default_factory=list)
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_status: EvidenceStatus = EvidenceStatus.NOT_SPECIFIED
    what_to_verify: List[str] = Field(default_factory=list)
    evidence_score: int = 0
    claim_coverage: float = 0.0
    calculation_valid: bool = True

    # --- Internal metadata ---
    retrieved_chunks: List[Dict[str, Any]] = Field(default_factory=list)
    context_used: Optional[str] = None
    validation_issues: List[str] = Field(default_factory=list)
