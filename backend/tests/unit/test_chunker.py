"""
Unit tests for hierarchical chunker (FIN-016, FIN-017).
"""

import pytest
from app.ingestion.chunker import chunk_hierarchical, get_parent_for_child


def test_chunk_hierarchical_basic():
    pages = [
        {
            "page_number": 1,
            "text": "This is section 1. The interest rate is 10.5% per annum. Processing fee is 1% upfront.",
            "headings": [{"title": "Interest Rates", "level": 1}],
        },
        {
            "page_number": 2,
            "text": "This is section 2. Prepayment penalty of 2% applies if closed before 12 months.",
            "headings": [{"title": "Prepayment Terms", "level": 1}],
        }
    ]

    chunks = chunk_hierarchical(
        pages,
        child_token_size=50,
        parent_token_size=200,
        document_name="loan_agreement.pdf",
        product_name="Personal Loan A",
    )

    assert len(chunks) > 0
    child_chunks = [c for c in chunks if c["type"] == "child"]
    parent_chunks = [c for c in chunks if c["type"] == "parent"]

    assert len(child_chunks) >= 2
    assert len(parent_chunks) >= 2

    # Verify parent_chunk_id linkage (FIN-017)
    for child in child_chunks:
        assert child.get("parent_chunk_id") is not None
        assert child["document_name"] == "loan_agreement.pdf"
        assert child["product_name"] == "Personal Loan A"


def test_chunk_hierarchical_empty_pages():
    pages = []
    chunks = chunk_hierarchical(pages)
    assert chunks == []


def test_chunk_hierarchical_long_sentences():
    # Long text exceeding child token size
    long_sentence = "Loan term clause: " + ("The borrower agrees to terms and conditions. " * 30)
    pages = [
        {
            "page_number": 1,
            "text": long_sentence,
            "headings": [],
        }
    ]

    chunks = chunk_hierarchical(pages, child_token_size=40, parent_token_size=160)
    assert len(chunks) > 0
    assert any(c["type"] == "child" for c in chunks)


def test_get_parent_for_child():
    all_chunks = [
        {
            "type": "parent",
            "page_num": 1,
            "text": "Full clause containing child text. Prepayment penalty is 2%.",
        },
        {
            "type": "child",
            "page_num": 1,
            "text": "Prepayment penalty is 2%.",
        }
    ]

    parent_text = get_parent_for_child(all_chunks[1], all_chunks)
    assert "Full clause containing child text" in parent_text
