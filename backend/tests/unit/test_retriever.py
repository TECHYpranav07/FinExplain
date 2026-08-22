"""
Unit tests for dense, sparse, and hybrid retrieval logic (FIN-005, FIN-019, FIN-020).
"""

import pytest
from unittest.mock import patch, MagicMock
from app.rag.retrieval.dense_retriever import vector_search, MIN_SIMILARITY_SCORE
from app.rag.retrieval.hybrid_retriever import reciprocal_rank_fusion
from app.rag.retrieval.reranker import rerank_chunks


def test_dense_retriever_score_threshold():
    # Test that vector_search discards results below MIN_SIMILARITY_SCORE
    mock_index = MagicMock()
    mock_match_high = MagicMock()
    mock_match_high.id = "chunk_1"
    mock_match_high.score = 0.85
    mock_match_high.metadata = {"text": "High score text", "page_num": 1, "product_id": "p1"}

    mock_match_low = MagicMock()
    mock_match_low.id = "chunk_2"
    mock_match_low.score = 0.15  # Below 0.3 threshold
    mock_match_low.metadata = {"text": "Low score text", "page_num": 2, "product_id": "p1"}

    mock_index.query.return_value = MagicMock(matches=[mock_match_high, mock_match_low])

    with patch("app.external.pinecone_client.get_pinecone_index", return_value=mock_index), \
         patch("app.ingestion.embedder.generate_embedding", return_value=[0.1] * 384):
        results = vector_search("interest rate", ["p1"])
        assert len(results) == 1
        assert results[0]["id"] == "chunk_1"
        assert results[0]["score"] == 0.85


def test_reciprocal_rank_fusion():
    dense_results = [
        {"id": "doc_1", "text": "text 1", "score": 0.9},
        {"id": "doc_2", "text": "text 2", "score": 0.8},
    ]
    sparse_results = [
        {"id": "doc_2", "text": "text 2", "score": 0.95},
        {"id": "doc_3", "text": "text 3", "score": 0.7},
    ]

    fused = reciprocal_rank_fusion(dense_results, sparse_results, top_k=3)
    assert len(fused) == 3
    # doc_2 appears in both lists, so it should rank highest in RRF
    assert fused[0]["id"] == "doc_2"


def test_reranker_fallback_on_model_absence():
    chunks = [
        {"id": "c1", "text": "Interest rate is 10%"},
        {"id": "c2", "text": "Prepayment penalty is 2%"},
    ]
    # Reranker should not crash even if CrossEncoder is mock-failed
    with patch("app.rag.retrieval.reranker.get_reranker", return_value=None):
        results = rerank_chunks("interest rate query", chunks)
        assert len(results) == 2
        assert "rerank_score" in results[0]
        assert results[0]["rerank_score"] > 0
