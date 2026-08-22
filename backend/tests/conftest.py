"""
Shared test fixtures for FinExplain evidence pipeline tests.
"""

import pytest
from app.core.loan_categories import LoanFact, EvidenceStatus


# ---------------------------------------------------------------------------
# Sample chunks
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_chunks():
    """Minimal chunk dicts simulating retrieved results."""
    return [
        {
            "id": "chunk_100",
            "chunk_id": "chunk_100",
            "document_id": "doc_1",
            "product_id": "prod_1",
            "document_name": "Product_A_Terms.pdf",
            "product_name": "Product A",
            "page_number": 8,
            "page_num": 8,
            "section_title": "Fee Schedule",
            "text": "A processing fee of 2% of the approved loan amount applies.",
            "rerank_score": 0.85,
            "chunk_type": "child",
        },
        {
            "id": "chunk_101",
            "chunk_id": "chunk_101",
            "document_id": "doc_1",
            "product_id": "prod_1",
            "document_name": "Product_A_Terms.pdf",
            "product_name": "Product A",
            "page_number": 12,
            "page_num": 12,
            "section_title": "Early Repayment",
            "text": "Early repayment fee is waived after 12 months.",
            "rerank_score": 0.80,
            "chunk_type": "child",
        },
        {
            "id": "chunk_200",
            "chunk_id": "chunk_200",
            "document_id": "doc_2",
            "product_id": "prod_2",
            "document_name": "Product_B_Terms.pdf",
            "product_name": "Product B",
            "page_number": 5,
            "page_num": 5,
            "section_title": "Fee Schedule",
            "text": "Processing fee is 1% of the loan amount.",
            "rerank_score": 0.82,
            "chunk_type": "child",
        },
        {
            "id": "chunk_201",
            "chunk_id": "chunk_201",
            "document_id": "doc_2",
            "product_id": "prod_2",
            "document_name": "Product_B_Terms.pdf",
            "product_name": "Product B",
            "page_number": 8,
            "page_num": 8,
            "section_title": "Fee Schedule",
            "text": "Processing fee is 2% of the loan amount.",
            "rerank_score": 0.78,
            "chunk_type": "child",
        },
        {
            "id": "chunk_300",
            "chunk_id": "chunk_300",
            "document_id": "doc_3",
            "product_id": "prod_1",
            "document_name": "Product_A_Addendum.pdf",
            "product_name": "Product A",
            "page_number": 3,
            "page_num": 3,
            "section_title": "Charges",
            "text": "The total processing cost is $2,000.",
            "rerank_score": 0.70,
            "chunk_type": "child",
        },
        {
            "id": "chunk_301",
            "chunk_id": "chunk_301",
            "document_id": "doc_3",
            "product_id": "prod_1",
            "document_name": "Product_A_Addendum.pdf",
            "product_name": "Product A",
            "page_number": 3,
            "page_num": 3,
            "section_title": "Charges",
            "text": "The total processing cost is €2,000.",
            "rerank_score": 0.68,
            "chunk_type": "child",
        },
    ]


# ---------------------------------------------------------------------------
# Sample LoanFacts
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_facts():
    """Pre-built LoanFact objects for testing."""
    return [
        LoanFact(
            category="processing_fee",
            field="processing_fee",
            value="2",
            unit="percent",
            source_document="Product_A_Terms.pdf",
            page=8,
            section="Fee Schedule",
            source_chunk_id="chunk_100",
            source_text="A processing fee of 2% of the approved loan amount applies.",
            status=EvidenceStatus.EXPLICIT,
            confidence=0.9,
        ),
        LoanFact(
            category="early_repayment",
            field="early_repayment_fee",
            value="waived",
            condition="after 12 months",
            source_document="Product_A_Terms.pdf",
            page=12,
            section="Early Repayment",
            source_chunk_id="chunk_101",
            source_text="Early repayment fee is waived after 12 months.",
            status=EvidenceStatus.CONDITIONAL,
            confidence=0.85,
        ),
        LoanFact(
            category="processing_fee",
            field="processing_fee",
            value="1",
            unit="percent",
            source_document="Product_B_Terms.pdf",
            page=5,
            section="Fee Schedule",
            source_chunk_id="chunk_200",
            source_text="Processing fee is 1% of the loan amount.",
            status=EvidenceStatus.EXPLICIT,
            confidence=0.9,
        ),
    ]
