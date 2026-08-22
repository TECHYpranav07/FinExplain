"""
Unit tests for evidence scoring, claim verification, and response validation.
"""

import pytest
from app.rag.verification.confidence import EvidenceScorer
from app.rag.verification.claim_verifier import verify_claim
from app.core.loan_categories import LoanFact, EvidenceStatus


def test_evidence_scorer_high_confidence():
    scorer = EvidenceScorer()
    claim_results = {
        "total_claims": 3,
        "supported_claims": 3,
        "unsupported_claims": 0,
        "invalid_citations": 0,
        "conditions_dropped": 0,
        "claim_coverage": 1.0,
    }
    facts = [
        LoanFact(field="interest_rate", category="interest_rate", value="10%", status=EvidenceStatus.EXPLICIT),
        LoanFact(field="processing_fee", category="processing_fee", value="1%", status=EvidenceStatus.EXPLICIT),
    ]
    res = scorer.calculate_evidence_score(
        claim_results=claim_results,
        facts=facts,
        conflicts=[],
        missing=[],
        rerank_scores=[0.9, 0.85],
    )
    assert res["score"] >= 80
    assert res["label"] == "High"


def test_evidence_scorer_conflict_penalty():
    scorer = EvidenceScorer()
    claim_results = {
        "total_claims": 2,
        "supported_claims": 1,
        "unsupported_claims": 1,
        "invalid_citations": 0,
        "conditions_dropped": 0,
        "claim_coverage": 0.5,
    }
    conflicts = [{"field": "interest_rate", "conflict": True, "values": ["10%", "12%"]}]
    res = scorer.calculate_evidence_score(
        claim_results=claim_results,
        facts=[],
        conflicts=conflicts,
        missing=[],
    )
    assert res["score"] < 60
    assert res["label"] in ("Low", "Medium")


def test_verify_claim_unsupported_when_no_facts():
    claim = {"claim": "Guaranteed zero processing fee for everyone.", "type": "value"}
    res = verify_claim(claim, [], [])
    assert res["supported"] is False
    assert res["status"] == "NOT_SPECIFIED"
