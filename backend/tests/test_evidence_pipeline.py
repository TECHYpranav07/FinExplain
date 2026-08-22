"""
Comprehensive 20-Scenario Automated Test Suite for FinExplain Evidence Pipeline.

All tests are deterministic and run WITHOUT external services
(no LLM, no Pinecone, no Supabase).

Scenarios tested:
  1. Explicit fee
  2. Conditional fee
  3. Missing fee
  4. Conflicting fee
  5. Early repayment penalty
  6. Fee waiver
  7. Late payment penalty
  8. Missing late-payment amount
  9. Variable interest rate
  10. Conflicting APR
  11. Currency conflict
  12. Scenario-specific prepayment risk (tenure vs waiver timing)
  13. Missing calculation input
  14. Unsupported LLM claim penalty
  15. Invalid citation page check
  16. Correct "NOT_SPECIFIED" response
  17. Correct "MIXED" response
  18. Correct deterministic calculation
  19. Risk score calculation & levels
  20. Evidence confidence calculation (multi-dimensional)
"""

import pytest
from types import SimpleNamespace
from app.core.loan_categories import LoanFact, EvidenceStatus, REQUIRED_COMPARISON_FIELDS
from app.rag.extraction import fact_extractor
from app.rag.extraction.condition_detector import detect_conditions, annotate_facts_with_conditions
from app.rag.extraction.missing_detector import detect_missing_information
from app.rag.verification.conflict_detector import detect_fact_conflicts
from app.rag.verification.confidence import EvidenceScorer
from app.rag.verification.claim_verifier import verify_claim
from app.rag.verification.response_validator import validate_final_response
from app.rag.extraction.cost_driver_detector import detect_cost_drivers
from app.rag.extraction.risk_engine import RiskEngine, RiskSeverity
from app.rag.extraction.lender_questions import generate_lender_questions
from app.tools.calculator import (
    calculate_processing_fee,
    calculate_loan_scenario,
    calculate_monthly_payment,
)


# =========================================================================
# Scenario 1 — Explicit fee
# =========================================================================
def test_scenario_01_explicit_fee(sample_facts):
    proc_fee = sample_facts[0]
    assert proc_fee.status == EvidenceStatus.EXPLICIT
    assert proc_fee.value == "2"
    assert proc_fee.unit == "percent"


# =========================================================================
# Scenario 2 — Conditional fee
# =========================================================================
def test_scenario_02_conditional_fee(sample_facts):
    fact = LoanFact(
        category="processing_fee",
        field="processing_fee",
        value="1",
        condition="if applied online",
        source_text="Processing fee is 1% if applied online.",
        status=EvidenceStatus.EXPLICIT,  # will be corrected
    )
    annotated = annotate_facts_with_conditions([fact])
    assert annotated[0].status == EvidenceStatus.CONDITIONAL
    assert "online" in annotated[0].condition


# =========================================================================
# Scenario 3 — Missing fee
# =========================================================================
def test_scenario_03_missing_fee():
    facts = [
        LoanFact(category="interest_rate", field="interest_rate", value="9.5%", status=EvidenceStatus.EXPLICIT)
    ]
    missing = detect_missing_information(facts)
    missing_fields = [m["field"] for m in missing]
    assert "processing_fee" in missing_fields
    assert any(m["status"] == "NOT_SPECIFIED" for m in missing if m["field"] == "processing_fee")


# =========================================================================
# Scenario 4 — Conflicting fee
# =========================================================================
def test_scenario_04_conflicting_fee(sample_facts):
    conflicts = detect_fact_conflicts(sample_facts)
    assert len(conflicts) > 0
    assert conflicts[0]["status"] == "MIXED"
    assert conflicts[0]["conflict"] is True


# =========================================================================
# Scenario 5 — Early repayment penalty
# =========================================================================
def test_scenario_05_early_repayment_penalty():
    fact = LoanFact(
        category="early_repayment",
        field="early_repayment_fee",
        value="3%",
        condition="before 24 months",
        status=EvidenceStatus.CONDITIONAL,
        source_chunk_id="chunk_101",
    )
    engine = RiskEngine()
    risks = engine.detect_risk_factors([fact], [], [])
    repayment_risks = [r for r in risks if r["category"] == "REPAYMENT_RISK"]
    assert len(repayment_risks) > 0


# =========================================================================
# Scenario 6 — Fee waiver
# =========================================================================
def test_scenario_06_fee_waiver():
    fact = LoanFact(
        category="fee_waiver",
        field="processing_fee_waiver",
        value="100%",
        condition="for defense personnel",
        status=EvidenceStatus.CONDITIONAL,
    )
    assert fact.status == EvidenceStatus.CONDITIONAL
    assert fact.condition == "for defense personnel"


# =========================================================================
# Scenario 7 — Late payment penalty
# =========================================================================
def test_scenario_07_late_payment_penalty():
    fact = LoanFact(
        category="late_payment",
        field="late_payment_fee",
        value="₹500 + 2% per month",
        status=EvidenceStatus.EXPLICIT,
    )
    engine = RiskEngine()
    risks = engine.detect_risk_factors([fact], [], [])
    penalty_risks = [r for r in risks if r["category"] == "PENALTY_RISK"]
    assert len(penalty_risks) > 0
    assert penalty_risks[0]["severity"] in (RiskSeverity.HIGH, RiskSeverity.MEDIUM)


# =========================================================================
# Scenario 8 — Missing late-payment amount
# =========================================================================
def test_scenario_08_missing_late_payment_amount():
    fact = LoanFact(
        category="late_payment",
        field="late_payment_fee",
        value=None,  # Mentioned but unquantified
        source_text="Late payment charges may be levied as per bank policy.",
        status=EvidenceStatus.CONDITIONAL,
    )
    engine = RiskEngine()
    risks = engine.detect_risk_factors([fact], [], [])
    info_gaps = [r for r in risks if r["category"] == "INFORMATION_GAP"]
    assert len(info_gaps) > 0


# =========================================================================
# Scenario 9 — Variable interest rate
# =========================================================================
def test_scenario_09_variable_interest():
    fact = LoanFact(
        category="interest_rate",
        field="interest_rate",
        value="8.5% floating (linked to repo rate)",
        status=EvidenceStatus.EXPLICIT,
    )
    engine = RiskEngine()
    risks = engine.detect_risk_factors([fact], [], [])
    rate_risks = [r for r in risks if r["category"] == "RATE_RISK"]
    assert len(rate_risks) > 0
    assert rate_risks[0]["severity"] == RiskSeverity.HIGH


# =========================================================================
# Scenario 10 — Conflicting APR
# =========================================================================
def test_scenario_10_conflicting_apr():
    facts = [
        LoanFact(
            category="apr", field="apr", value="10.5%",
            source_document="Doc_A.pdf", page=1, status=EvidenceStatus.EXPLICIT
        ),
        LoanFact(
            category="apr", field="apr", value="12.0%",
            source_document="Doc_B.pdf", page=2, status=EvidenceStatus.EXPLICIT
        ),
    ]
    conflicts = detect_fact_conflicts(facts)
    assert len(conflicts) > 0
    assert conflicts[0]["field"] == "apr"
    assert conflicts[0]["status"] == "MIXED"


# =========================================================================
# Scenario 11 — Currency conflict
# =========================================================================
def test_scenario_11_currency_conflict():
    facts = [
        LoanFact(category="processing_fee", field="processing_fee", value="2000", currency="USD", source_document="doc_A.pdf", page=1, status=EvidenceStatus.EXPLICIT),
        LoanFact(category="processing_fee", field="processing_fee", value="2000", currency="EUR", source_document="doc_B.pdf", page=1, status=EvidenceStatus.EXPLICIT),
    ]
    conflicts = detect_fact_conflicts(facts)
    assert len(conflicts) > 0
    assert conflicts[0]["status"] == "MIXED"


# =========================================================================
# Scenario 12 — Scenario-specific prepayment risk
# =========================================================================
def test_scenario_12_scenario_specific_prepayment_risk():
    fact = LoanFact(
        category="early_repayment",
        field="early_repayment_fee",
        value="waived",
        condition="after 12 months",
        source_text="Prepayment fee is waived after 12 months.",
        status=EvidenceStatus.CONDITIONAL,
    )
    engine = RiskEngine()

    # User plans 6-month repayment (before waiver!)
    scenario_6m = {"principal": 1000000, "repayment_period": 6, "repayment_unit": "months"}
    risks_6m = engine.detect_risk_factors([fact], [], [], scenario=scenario_6m)
    scenario_risks = [r for r in risks_6m if r["category"] == "SCENARIO_SPECIFIC_RISK"]
    assert len(scenario_risks) > 0
    assert scenario_risks[0]["severity"] == RiskSeverity.HIGH

    # User plans 24-month repayment (after waiver!)
    scenario_24m = {"principal": 1000000, "repayment_period": 24, "repayment_unit": "months"}
    risks_24m = engine.detect_risk_factors([fact], [], [], scenario=scenario_24m)
    waived_risks = [r for r in risks_24m if r["severity"] == RiskSeverity.LOW]
    assert len(waived_risks) > 0


# =========================================================================
# Scenario 13 — Missing calculation input
# =========================================================================
def test_scenario_13_missing_calculation_input():
    result = calculate_loan_scenario(
        principal=500000,
        interest_rate=None,  # Missing!
        tenure=12,
    )
    assert "interest_rate" in result["unknown_costs"]
    assert "emi" not in result["results"]


# =========================================================================
# Scenario 14 — Unsupported LLM claim penalty
# =========================================================================
def test_scenario_14_unsupported_claim_penalty(sample_facts, sample_chunks):
    claim = {
        "claim": "Student loan discount of 50% is guaranteed.",
        "type": "value",
        "cited_page": None,
    }
    verification = verify_claim(claim, sample_facts, sample_chunks)
    assert verification["supported"] is False

    scorer = EvidenceScorer()
    claim_results = {
        "total_claims": 2,
        "supported_claims": 1,
        "unsupported_claims": 1,
        "invalid_citations": 0,
        "conditions_dropped": 0,
        "claim_coverage": 0.5,
    }
    score_res = scorer.calculate_evidence_score(claim_results=claim_results)
    assert score_res["score"] <= 59


# =========================================================================
# Scenario 15 — Invalid citation page
# =========================================================================
def test_scenario_15_invalid_citation_page(sample_facts, sample_chunks):
    answer = "Processing fee is 2%. [Page 999]"
    claim_results = {
        "claims": [{"claim": "fee is 2%", "supported": True, "citation_valid": True, "condition_preserved": True}],
        "total_claims": 1,
        "supported_claims": 1,
        "unsupported_claims": 0,
        "invalid_citations": 0,
        "conditions_dropped": 0,
    }
    validation = validate_final_response(answer, claim_results, sample_facts, sample_chunks)
    assert validation["valid"] is False
    assert any("Page 999" in i for i in validation["issues"])


# =========================================================================
# Scenario 16 — Correct NOT_SPECIFIED response
# =========================================================================
def test_scenario_16_not_specified_handling():
    facts = []
    missing = detect_missing_information(facts)
    for m in missing:
        assert m["status"] == "NOT_SPECIFIED"
        assert "No supporting clause" in m["reason"]


# =========================================================================
# Scenario 17 — Correct MIXED response
# =========================================================================
def test_scenario_17_mixed_status_handling(sample_facts):
    conflicts = detect_fact_conflicts(sample_facts)
    assert len(conflicts) > 0
    assert conflicts[0]["status"] == "MIXED"


# =========================================================================
# Scenario 18 — Correct deterministic calculation
# =========================================================================
def test_scenario_18_deterministic_calculation():
    # 500,000 * 2% = 10,000
    res = calculate_processing_fee(500000, 2.0, fee_type="percent")
    assert res["result"] == 10000.0
    assert "500000" in res["formula"]

    emi = calculate_monthly_payment(500000, 12.0, 12)
    assert round(emi, 2) == 44424.39


# =========================================================================
# Scenario 19 — Risk score calculation & levels
# =========================================================================
def test_scenario_19_risk_score_calculation():
    engine = RiskEngine()
    # High risk combination: conflict + scenario penalty + high cost
    risks = [
        {"category": "DOCUMENT_CONFLICT", "severity": RiskSeverity.HIGH},
        {"category": "SCENARIO_SPECIFIC_RISK", "severity": RiskSeverity.HIGH},
        {"category": "COST_RISK", "severity": RiskSeverity.HIGH},
    ]
    res = engine.calculate_risk_score(risks)
    assert res["score"] >= 61
    assert res["level"] in ("HIGH", "VERY HIGH")


# =========================================================================
# Scenario 20 — Evidence confidence calculation
# =========================================================================
def test_scenario_20_evidence_confidence_calculation():
    scorer = EvidenceScorer()
    claim_results = {
        "total_claims": 4,
        "supported_claims": 4,
        "unsupported_claims": 0,
        "invalid_citations": 0,
        "conditions_dropped": 0,
        "claim_coverage": 1.0,
    }
    facts = [
        LoanFact(category="processing_fee", field="processing_fee", value="2%", page=1, section="Fees", status=EvidenceStatus.EXPLICIT)
    ]
    res = scorer.calculate_evidence_score(claim_results=claim_results, facts=facts)
    assert res["score"] >= 75
    assert res["label"] == "High"
    assert "citation_validity" in res["dimensions"]
    assert "claim_evidence_support" in res["dimensions"]


def test_claim_verifier_rejects_mismatched_numeric_value():
    fact = LoanFact(
        category="processing_fee",
        field="processing_fee",
        value="2",
        status=EvidenceStatus.EXPLICIT,
        source_chunk_id="chunk_fee",
    )
    result = verify_claim(
        {"claim": "The processing fee is 12%.", "type": "value"},
        [fact],
        [{"id": "chunk_fee", "page_number": 1, "text": "Processing fee is 2%."}],
    )
    assert result["supported"] is False


def test_fact_extractor_preserves_multi_document_source(monkeypatch):
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=(
                        '[{"category":"processing_fee",'
                        '"field":"processing_fee","value":"2",'
                        '"page":1,"source_text":"Fee is 2%.",'
                        '"status":"EXPLICIT"}]'
                    )
                )
            )
        ]
    )
    monkeypatch.setattr(
        fact_extractor.client.chat.completions,
        "create",
        lambda **kwargs: response,
    )
    facts = fact_extractor.extract_structured_facts(
        [
            {"id": "a", "document_name": "A.pdf", "page_number": 1, "text": "Fee is 1%."},
            {"id": "b", "document_name": "B.pdf", "page_number": 1, "text": "Fee is 2%."},
        ],
        document_name="fallback.pdf",
    )
    assert facts[0].source_chunk_id == "b"
    assert facts[0].source_document == "B.pdf"
