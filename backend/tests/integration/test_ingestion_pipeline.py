"""
Integration tests for document ingestion pipeline (FIN-011, FIN-013, FIN-017, FIN-030).
"""

import pytest
from unittest.mock import patch, MagicMock
from app.ingestion.pipeline import process_document


def test_ingestion_pipeline_with_mocked_stores():
    mock_pdf_bytes = b"%PDF-1.4 Mock PDF Content with interest rate 10.5%"
    mock_parsed = {
        "full_text": "Interest rate is 10.5% per annum.",
        "pages": [
            {
                "page_number": 1,
                "text": "Interest rate is 10.5% per annum.",
                "headings": [{"title": "Terms", "level": 1}],
            }
        ],
        "total_pages": 1,
        "document_metadata": {"document_version": "1.0", "effective_date": "2026-01-01"},
    }

    mock_product = {"id": "1", "name": "Sample Home Loan A"}
    mock_doc = {"id": "doc_test_123", "status": "processing"}

    with patch("app.ingestion.pipeline.get_document_by_hash", return_value=None), \
         patch("app.ingestion.pipeline.get_product_by_id", return_value=mock_product), \
         patch("app.ingestion.pipeline.parse_document", return_value=mock_parsed), \
         patch("app.ingestion.pipeline.parse_pdf", return_value=mock_parsed), \
         patch("app.ingestion.pipeline.create_document", return_value=mock_doc), \
         patch("app.ingestion.embedder.generate_embeddings", return_value=[[0.1] * 384]), \
         patch("app.ingestion.pipeline.get_pinecone_index", return_value=MagicMock()), \
         patch("app.ingestion.pipeline.insert_chunks", return_value=[{"id": "chunk_1"}]), \
         patch("app.ingestion.pipeline.update_document_status") as mock_update_status:

        result = process_document(
            file_bytes=mock_pdf_bytes,
            file_name="test_agreement.pdf",
            product_id="1",
        )

        assert result["status"] == "success"
        assert result["document_id"] == "doc_test_123"
        mock_update_status.assert_called_with("doc_test_123", "indexed")


def test_ingestion_pipeline_marks_failed_on_error():
    mock_pdf_bytes = b"%PDF-1.4 Mock PDF Content"
    mock_parsed = {
        "full_text": "Sample text",
        "pages": [{"page_num": 1, "text": "Sample text"}],
        "total_pages": 1,
        "document_metadata": {},
    }
    mock_doc = {"id": "doc_fail_123", "status": "processing"}

    with patch("app.ingestion.pipeline.get_document_by_hash", return_value=None), \
         patch("app.ingestion.pipeline.get_product_by_id", return_value={"id": "1", "name": "Prod"}), \
         patch("app.ingestion.pipeline.parse_document", return_value=mock_parsed), \
         patch("app.ingestion.pipeline.parse_pdf", return_value=mock_parsed), \
         patch("app.ingestion.pipeline.create_document", return_value=mock_doc), \
         patch("app.ingestion.pipeline.chunk_hierarchical", side_effect=ValueError("Chunking error")), \
         patch("app.ingestion.pipeline.update_document_status") as mock_update_status:

        with pytest.raises(ValueError):
            process_document(
                file_bytes=mock_pdf_bytes,
                file_name="corrupt.pdf",
                product_id="1",
            )

        # Ingestion should mark status as failed (FIN-013)
        mock_update_status.assert_called_with("doc_fail_123", "failed")
