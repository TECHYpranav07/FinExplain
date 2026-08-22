"""
Core loan taxonomy, evidence status definitions, and structured data models
for the FinExplain evidence-first pipeline.
"""

from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Evidence status — deterministic, never assigned by LLM confidence alone
# ---------------------------------------------------------------------------

class EvidenceStatus(str, Enum):
    EXPLICIT = "EXPLICIT"          # Document clearly states the information
    CONDITIONAL = "CONDITIONAL"    # Applies only under a stated condition / illustrative
    MIXED = "MIXED"                # Conflicting information across sources
    NOT_SPECIFIED = "NOT_SPECIFIED" # Documents do not contain the information


# ---------------------------------------------------------------------------
# Standard loan categories — fixed taxonomy
# ---------------------------------------------------------------------------

LOAN_CATEGORIES: List[str] = [
    "loan_amount",
    "interest_rate",
    "apr",
    "processing_fee",
    "origination_fee",
    "administrative_fee",
    "documentation_fee",
    "other_fee",
    "early_repayment",
    "prepayment",
    "foreclosure",
    "partial_prepayment",
    "late_payment",
    "default_penalty",
    "default_interest",
    "repayment_schedule",
    "loan_tenure",
    "monthly_emi",
    "grace_period",
    "fee_waiver",
    "eligibility",
    "income_requirement",
    "credit_requirement",
    "employment_requirement",
    "residency_requirement",
    "exclusion",
    "exception",
    "condition",
    "effective_date",
    "expiry_date",
    "document_version",
    "currency",
]


# ---------------------------------------------------------------------------
# Canonical field synonym mapping
# ---------------------------------------------------------------------------

FIELD_SYNONYMS: Dict[str, List[str]] = {
    "early_repayment": [
        "early_repayment",
        "early_repayment_fee",
        "early_repayment_charge",
        "prepayment",
        "pre_payment",
        "prepayment_charge",
        "prepayment_fee",
        "prepayment_penalty",
        "foreclosure",
        "foreclosure_charge",
        "foreclosure_fee",
        "early_settlement",
        "loan_settlement",
        "pre_closure",
        "preclosure",
        "partial_prepayment",
        "prepayment charge",
        "early repayment",
    ],
    "late_payment": [
        "late_payment",
        "late_payment_fee",
        "late_fee",
        "late_payment_charge",
        "default_penalty",
        "default_fee",
        "delayed_payment",
        "overdue_fee",
        "overdue_charge",
        "penalty_charge",
        "default_interest",
        "late payment fee",
        "late fee",
    ],
    "processing_fee": [
        "processing_fee",
        "processing_charge",
        "origination_fee",
        "administrative_fee",
        "upfront_fee",
        "file_charge",
        "processing fee",
    ],
    "other_fee": [
        "other_fee",
        "documentation_fee",
        "document_charge",
        "documentation charge",
        "administrative_fee",
        "convenience_fee",
        "service_charge",
        "stamp_duty",
        "documentation fee",
    ],
    "interest_rate": [
        "interest_rate",
        "rate_of_interest",
        "roi",
        "fixed_rate",
        "floating_rate",
        "benchmark_rate",
        "annual_rate",
        "interest rate",
    ],
    "apr": [
        "apr",
        "annual_percentage_rate",
        "effective_rate",
        "effective_apr",
        "annual percentage rate",
    ],
    "loan_tenure": [
        "loan_tenure",
        "tenure",
        "term",
        "loan_term",
        "duration",
        "repayment_period",
        "loan tenure",
    ],
    "loan_amount": [
        "loan_amount",
        "principal",
        "sanctioned_amount",
        "borrowed_amount",
        "loan amount",
    ],
    "monthly_emi": [
        "monthly_emi",
        "emi",
        "monthly_payment",
        "installment",
        "installment_amount",
        "monthly emi",
    ],
    "repayment_schedule": [
        "repayment_schedule",
        "amortization_schedule",
        "emi_schedule",
        "installment_schedule",
        "repayment schedule",
    ],
    "fee_waiver": [
        "fee_waiver",
        "waiver",
        "discount",
        "concession",
        "fee waiver",
    ],
    "eligibility": [
        "eligibility",
        "income_requirement",
        "credit_requirement",
        "employment_requirement",
        "residency_requirement",
        "age_requirement",
    ],
}


def normalize_field_name(field_or_category: str) -> str:
    """
    Map any field or category variant to its canonical name.
    """
    clean = field_or_category.lower().replace("-", "_").replace(" ", "_").strip()
    for canonical, synonyms in FIELD_SYNONYMS.items():
        for syn in synonyms:
            syn_clean = syn.lower().replace("-", "_").replace(" ", "_").strip()
            if clean == syn_clean:
                return canonical
    return clean


# ---------------------------------------------------------------------------
# Required fields for a meaningful loan comparison
# ---------------------------------------------------------------------------

REQUIRED_COMPARISON_FIELDS: List[str] = [
    "apr",
    "interest_rate",
    "processing_fee",
    "other_fee",
    "early_repayment",
    "late_payment",
    "loan_tenure",
    "repayment_schedule",
]


# ---------------------------------------------------------------------------
# Structured Loan Fact model
# ---------------------------------------------------------------------------

class LoanFact(BaseModel):
    """A single structured fact extracted from a loan document."""

    category: str = Field(
        ..., description="One of the LOAN_CATEGORIES values or canonical names."
    )
    field: str = Field(
        ..., description="Specific field name, e.g. 'processing_fee'."
    )
    value: Optional[str] = Field(
        None, description="The extracted value as a string."
    )
    unit: Optional[str] = Field(
        None, description="Unit of the value, e.g. 'percent', 'months', 'INR'."
    )
    currency: Optional[str] = Field(None, description="Currency code if monetary.")
    condition: Optional[str] = Field(
        None, description="Condition under which this fact applies."
    )
    illustrative_only: bool = Field(
        default=False,
        description="Whether this charge/term is explicitly marked illustrative/sample only.",
    )
    effective_date: Optional[str] = Field(None)
    source_document: Optional[str] = Field(None, description="Document filename.")
    page: Optional[int] = Field(None, description="Page number in the source document.")
    section: Optional[str] = Field(None, description="Section title in the source document.")
    source_chunk_id: Optional[str] = Field(None, description="Chunk ID for traceability.")
    source_text: Optional[str] = Field(
        None, description="Verbatim text from the source chunk."
    )
    status: EvidenceStatus = Field(
        default=EvidenceStatus.NOT_SPECIFIED,
        description="Evidence status for this fact.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Extraction confidence (0–1).",
    )
