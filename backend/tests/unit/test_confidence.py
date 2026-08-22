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


def test_before_confirmation_checklist_generation():
    from app.rag.extraction.loan_analyzer import generate_before_confirmation_checklist
    facts = [
        LoanFact(field="interest_rate", category="interest_rate", value="10.5%", status=EvidenceStatus.EXPLICIT, page=1),
        LoanFact(field="prepayment_penalty", category="early_repayment", value="2%", condition="After 6 months", status=EvidenceStatus.CONDITIONAL, page=2),
    ]
    missing = [{"field": "late_payment_grace_period", "reason": "Not specified in document."}]
    conflicts = [{"field": "apr", "description": "KFS states 11.2% while Agreement states 12.0%", "values": ["11.2%", "12.0%"]}]

    checklist = generate_before_confirmation_checklist(facts, missing, conflicts)
    assert len(checklist) == 4

    # Check explicit item
    item1 = checklist[0]
    assert item1["marker"] == "✓"
    assert item1["priority"] == "HIGH"
    assert "suggested_question" in item1

    # Check conditional item
    item2 = checklist[1]
    assert item2["marker"] == "⚠"
    assert item2["condition"] == "After 6 months"

    # Check missing item
    item3 = checklist[2]
    assert item3["marker"] == "?"
    assert item3["category"] == "Missing Disclosures"

    # Check conflict item
    item4 = checklist[3]
    assert item4["marker"] == "🚨"
    assert item4["category"] == "Contract Discrepancies"


def test_before_confirmation_deterministic_fallback():
    from app.rag.generation.generator import _synthesize_deterministic_checklist
    facts = [{"field": "interest_rate", "category": "interest_rate", "value": "10.5%", "status": "EXPLICIT", "page": 1}]
    missing = [{"field": "bounce_charges", "reason": "Omitted"}]
    conflicts = [{"field": "tenure", "description": "Contradiction"}]

    markdown = _synthesize_deterministic_checklist(facts, missing, conflicts)
    assert "Before You Confirm" in markdown
    assert "Mandatory Pre-Signing Verification Checklist" in markdown
    assert "Actionable Questions to Ask Your Lender" in markdown
    assert "10.5%" in markdown

