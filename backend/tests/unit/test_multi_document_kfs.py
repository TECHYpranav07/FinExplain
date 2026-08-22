"""
Unit tests for Indian Retail Loan Multi-Document (KFS vs Agreement) Architecture.
"""

from app.tools.calculator import calculate_early_repayment_penalty
from app.rag.verification.conflict_detector import detect_fact_conflicts
from app.core.loan_categories import LoanFact, EvidenceStatus


def test_early_repayment_penalty_distinguishes_outstanding_principal():
    # When outstanding principal is unknown, engine must NOT use sanctioned amount silently
    result = calculate_early_repayment_penalty(
        penalty_rate=3.0,
        outstanding_principal=None,
        original_principal=500000.0,
    )
    assert result["result"] is None
    assert "current_outstanding_principal" in result["unknown_inputs"]
    assert "3.0% × [Current Outstanding Principal]" in result["formula"]


def test_early_repayment_penalty_calculates_when_outstanding_known():
    result = calculate_early_repayment_penalty(
        penalty_rate=3.0,
        outstanding_principal=350000.0,
    )
    assert result["result"] == 10500.0
    assert "350000.0 × 3.0% = 10500.0" in result["formula"]


def test_early_repayment_waiver_after_lockin():
    result = calculate_early_repayment_penalty(
        penalty_rate=5.0,
        outstanding_principal=400000.0,
        lock_in_months=12,
        current_month=14,
    )
    assert result["is_waived"] is True
    assert result["result"] == 0.0


def test_kfs_vs_loan_agreement_conflict_detection():
    fact_kfs = LoanFact(
        category="prepayment",
        field="prepayment_penalty",
        value="3%",
        source_document="KFS.pdf",
        page=2,
        status=EvidenceStatus.EXPLICIT,
    )
    fact_agreement = LoanFact(
        category="prepayment",
        field="prepayment_penalty",
        value="5%",
        source_document="Loan_Agreement.pdf",
        page=8,
        status=EvidenceStatus.EXPLICIT,
    )

    conflicts = detect_fact_conflicts([fact_kfs, fact_agreement])
    assert len(conflicts) == 1
    assert conflicts[0]["field"] == "early_repayment"
    assert conflicts[0]["status"] == "MIXED"
    assert conflicts[0]["values"][0]["document"] == "KFS.pdf"
    assert conflicts[0]["values"][1]["document"] == "Loan_Agreement.pdf"
