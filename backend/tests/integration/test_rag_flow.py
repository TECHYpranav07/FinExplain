"""
Integration tests for the complete RAG orchestrator flow with mocked external LLM/vector services.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.rag.orchestrator import process_query
from app.core.loan_categories import LoanFact, EvidenceStatus
from app.cache.query_cache import clear_cache


def test_rag_flow_end_to_end():
    clear_cache()
    mock_chunks = [
        {
            "id": "chunk_1",
            "document_id": "doc_1",
            "product_id": "1",
            "document_name": "sample_loan.pdf",
            "product_name": "Sample Home Loan A",
            "page_number": 1,
            "section_title": "Interest Rate",
            "text": "The applicable interest rate is 10.50% per annum. Processing fee is 1.00% of loan amount.",
            "rerank_score": 0.92,
        }
    ]

    mock_intent = MagicMock()
    mock_intent.intent = "lookup"
    mock_intent.confidence = 0.9

    mock_facts = [
        LoanFact(
            field="interest_rate",
            category="interest_rate",
            value="10.50%",
            source_document="sample_loan.pdf",
            page=1,
            source_chunk_id="chunk_1",
            status=EvidenceStatus.EXPLICIT,
        ),
        LoanFact(
            field="processing_fee",
            category="processing_fee",
            value="1.00%",
            source_document="sample_loan.pdf",
            page=1,
            source_chunk_id="chunk_1",
            status=EvidenceStatus.EXPLICIT,
        ),
    ]

    with patch("app.rag.orchestrator.get_cached_response", return_value=None), \
         patch("app.rag.orchestrator.classify_intent", return_value=mock_intent), \
         patch("app.rag.orchestrator.rewrite_query", return_value="What is the interest rate?"), \
         patch("app.rag.orchestrator.hybrid_search", return_value=mock_chunks), \
         patch("app.rag.orchestrator.rerank_chunks", return_value=mock_chunks), \
         patch("app.rag.orchestrator.get_all_facts", return_value=mock_facts), \
         patch("app.rag.orchestrator.extract_structured_facts", return_value=mock_facts), \
         patch("app.rag.orchestrator.generate_answer", return_value={"answer": "The interest rate is 10.50% [Page 1]. Processing fee is 1.00% [Page 1]."}):

        result = process_query(
            question="What is the interest rate and fee?",
            product_ids=["1"],
        )

        assert result is not None
        assert "answer" in result
        assert result["intent"] == "lookup"
        assert len(result["key_facts"]) == 2
        assert result["evidence_status"] == "EXPLICIT"
        assert len(result["evidence"]) == 2
        # Check verified field (FIN-006)
        assert any(e["verified"] is True for e in result["evidence"])


def test_rag_flow_no_evidence_returns_zero_confidence():
    mock_intent = MagicMock()
    mock_intent.intent = "lookup"
    mock_intent.confidence = 0.5

    with patch("app.rag.orchestrator.get_cached_response", return_value=None), \
         patch("app.rag.orchestrator.classify_intent", return_value=mock_intent), \
         patch("app.rag.orchestrator.hybrid_search", return_value=[]):

        result = process_query(
            question="What is the cosmic rate?",
            product_ids=["1"],
        )

        assert result["confidence_score"] == 0.0
        assert result["confidence_label"] == "No Evidence"
        assert "No relevant information" in result["answer"]
