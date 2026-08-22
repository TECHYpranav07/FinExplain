"""
Financial Risk Factor Detection and Deterministic Risk Scoring Engine.

Separates Financial Risk from Evidence Confidence:
- Evidence Confidence: How strongly is the answer supported by source documents?
- Financial Risk: What potentially costly or unfavorable conditions exist for the borrower?
- Evidence Status: What type of evidence supports the finding (EXPLICIT, CONDITIONAL, MIXED, NOT_SPECIFIED)?

Categories:
1. COST RISK
2. REPAYMENT RISK
3. PENALTY RISK
4. CONDITION RISK
5. ELIGIBILITY RISK
6. INFORMATION GAP
7. DOCUMENT CONFLICT
8. RATE RISK
9. SCENARIO-SPECIFIC RISK
"""

import re
from typing import List, Dict, Any, Optional
from app.core.loan_categories import LoanFact, EvidenceStatus

# Configurable thresholds
DEFAULT_HIGH_PROCESSING_FEE_PCT = 2.0  # >= 2.0% is flagged
DEFAULT_HIGH_FIXED_FEE_RATIO = 0.02    # >= 2% of principal

DEFAULT_RISK_WEIGHTS: Dict[str, int] = {
    "high_cost": 20,
    "prepayment_penalty": 20,
    "late_payment_penalty": 15,
    "conditional_fee": 10,
    "missing_critical_information": 20,
    "document_conflict": 20,
    "variable_rate": 10,
    "scenario_specific_penalty": 25,
}

class RiskSeverity:
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

class RiskEngine:
    """
    Deterministic risk factor detection and scoring engine.
    """
    def __init__(
        self,
        weights: Optional[Dict[str, int]] = None,
        high_fee_pct_threshold: float = DEFAULT_HIGH_PROCESSING_FEE_PCT,
        high_fixed_fee_ratio: float = DEFAULT_HIGH_FIXED_FEE_RATIO,
    ):
        self.weights = weights or dict(DEFAULT_RISK_WEIGHTS)
        self.high_fee_pct_threshold = high_fee_pct_threshold
        self.high_fixed_fee_ratio = high_fixed_fee_ratio

    def detect_risk_factors(
        self,
        facts: List[LoanFact],
        missing: List[Dict[str, Any]],
        conflicts: List[Dict[str, Any]],
        scenario: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Identify structured risk factors across 9 dimensions.
        """
        risks: List[Dict[str, Any]] = []
        scenario = scenario or {}
        user_tenure_months = scenario.get("repayment_period")
        if scenario.get("repayment_unit") in ("years", "year") and user_tenure_months:
            user_tenure_months = user_tenure_months * 12
        principal = scenario.get("principal")

        # 1. COST RISK
        for fact in facts:
            if fact.category in ("processing_fee", "origination_fee", "administrative_fee", "documentation_fee", "other_fee"):
                try:
                    num_val = float(re.sub(r'[^\d.]', '', fact.value or '0'))
                    if fact.unit == "percent" or (fact.value and "%" in fact.value):
                        if num_val >= self.high_fee_pct_threshold:
                            risks.append({
                                "category": "COST_RISK",
                                "title": f"High {fact.field.replace('_', ' ').title()}",
                                "description": f"{fact.field.replace('_', ' ').title()} is {fact.value}{'%' if '%' not in str(fact.value) else ''}, which is at or above standard threshold ({self.high_fee_pct_threshold}%).",
                                "severity": RiskSeverity.HIGH if num_val > 3.0 else RiskSeverity.MEDIUM,
                                "field": fact.field,
                                "value": fact.value,
                                "status": fact.status.value,
                                "evidence_id": fact.source_chunk_id,
                            })
                    elif principal and num_val > 0:
                        ratio = num_val / principal
                        if ratio >= self.high_fixed_fee_ratio:
                            risks.append({
                                "category": "COST_RISK",
                                "title": f"Significant Fixed {fact.field.replace('_', ' ').title()}",
                                "description": f"Fixed fee of {num_val} represents {ratio*100:.1f}% of requested loan principal.",
                                "severity": RiskSeverity.HIGH if ratio > 0.05 else RiskSeverity.MEDIUM,
                                "field": fact.field,
                                "value": fact.value,
                                "status": fact.status.value,
                                "evidence_id": fact.source_chunk_id,
                            })
                except (ValueError, TypeError):
                    pass

        # 2. REPAYMENT RISK & 9. SCENARIO-SPECIFIC RISK
        for fact in facts:
            if fact.category in ("early_repayment", "prepayment", "foreclosure", "partial_prepayment"):
                condition_text = (fact.condition or fact.source_text or "").lower()
                
                # Check for waiver period timing
                waiver_months_match = re.search(r'(?:after|before|within)\s+(\d+)\s+month', condition_text)
                waiver_months = int(waiver_months_match.group(1)) if waiver_months_match else None

                # Scenario specific check
                if user_tenure_months is not None and waiver_months is not None:
                    if "after" in condition_text and user_tenure_months < waiver_months:
                        risks.append({
                            "category": "SCENARIO_SPECIFIC_RISK",
                            "title": "Prepayment Penalty Applies to Planned Scenario",
                            "description": f"User plans repayment in {user_tenure_months} months, but early repayment fee waiver only applies after {waiver_months} months.",
                            "severity": RiskSeverity.HIGH,
                            "field": fact.field,
                            "value": fact.value,
                            "status": fact.status.value,
                            "evidence_id": fact.source_chunk_id,
                        })
                    elif "before" in condition_text and user_tenure_months < waiver_months:
                        risks.append({
                            "category": "SCENARIO_SPECIFIC_RISK",
                            "title": "Prepayment Restriction in Planned Repayment Window",
                            "description": f"Early repayment penalty applies before {waiver_months} months; user plans to repay within {user_tenure_months} months.",
                            "severity": RiskSeverity.HIGH,
                            "field": fact.field,
                            "value": fact.value,
                            "status": fact.status.value,
                            "evidence_id": fact.source_chunk_id,
                        })
                    elif user_tenure_months >= waiver_months:
                        risks.append({
                            "category": "REPAYMENT_RISK",
                            "title": "Early Repayment Fee Waived For Scenario",
                            "description": f"Prepayment fee is waived after {waiver_months} months. Your planned {user_tenure_months}-month tenure qualifies for waiver.",
                            "severity": RiskSeverity.LOW,
                            "field": fact.field,
                            "value": fact.value,
                            "status": fact.status.value,
                            "evidence_id": fact.source_chunk_id,
                        })
                else:
                    # General repayment risk
                    if fact.status == EvidenceStatus.CONDITIONAL or "waiver" in condition_text or "fee" in condition_text:
                        risks.append({
                            "category": "REPAYMENT_RISK",
                            "title": f"Early Repayment Condition: {fact.field.replace('_', ' ').title()}",
                            "description": fact.condition or fact.source_text or "Early repayment is subject to specific conditions/fees.",
                            "severity": RiskSeverity.MEDIUM if fact.status == EvidenceStatus.CONDITIONAL else RiskSeverity.LOW,
                            "field": fact.field,
                            "value": fact.value,
                            "status": fact.status.value,
                            "evidence_id": fact.source_chunk_id,
                        })

        # 3. PENALTY RISK
        for fact in facts:
            if fact.category in ("late_payment", "default_penalty", "default_interest"):
                val = fact.value or ""
                if not val or val.lower() in ("null", "not specified", "none", "unknown"):
                    risks.append({
                        "category": "INFORMATION_GAP",
                        "title": f"Unspecified {fact.field.replace('_', ' ').title()} Amount",
                        "description": f"Documents mention a {fact.field.replace('_', ' ')} applies, but the exact amount/rate is not specified.",
                        "severity": RiskSeverity.MEDIUM,
                        "field": fact.field,
                        "value": "Unspecified",
                        "status": "NOT_SPECIFIED",
                        "evidence_id": fact.source_chunk_id,
                    })
                else:
                    risks.append({
                        "category": "PENALTY_RISK",
                        "title": f"Late Payment / Default Penalty: {fact.field.replace('_', ' ').title()}",
                        "description": f"Penalty terms: {fact.value} {fact.unit or ''}. {fact.condition or ''}".strip(),
                        "severity": RiskSeverity.HIGH if "default" in fact.category or "penalty" in fact.category else RiskSeverity.MEDIUM,
                        "field": fact.field,
                        "value": fact.value,
                        "status": fact.status.value,
                        "evidence_id": fact.source_chunk_id,
                    })

        # 4. CONDITION RISK
        for fact in facts:
            if fact.status == EvidenceStatus.CONDITIONAL and fact.category not in ("early_repayment", "prepayment"):
                risks.append({
                    "category": "CONDITION_RISK",
                    "title": f"Conditional Term: {fact.field.replace('_', ' ').title()}",
                    "description": f"Term applies conditionally: {fact.condition or fact.source_text}",
                    "severity": RiskSeverity.MEDIUM,
                    "field": fact.field,
                    "value": fact.value,
                    "status": "CONDITIONAL",
                    "evidence_id": fact.source_chunk_id,
                })

        # 5. ELIGIBILITY RISK
        for fact in facts:
            if fact.category in ("income_requirement", "credit_requirement", "employment_requirement", "residency_requirement", "exclusion"):
                risks.append({
                    "category": "ELIGIBILITY_RISK",
                    "title": f"Eligibility Restriction: {fact.field.replace('_', ' ').title()}",
                    "description": f"Requirement: {fact.value or fact.condition or fact.source_text}",
                    "severity": RiskSeverity.MEDIUM,
                    "field": fact.field,
                    "value": fact.value,
                    "status": fact.status.value,
                    "evidence_id": fact.source_chunk_id,
                })

        # 6. INFORMATION GAP
        for item in missing:
            risks.append({
                "category": "INFORMATION_GAP",
                "title": f"Missing Field: {item['field'].replace('_', ' ').title()}",
                "description": item.get("reason", "No supporting clause found in provided documents."),
                "severity": RiskSeverity.HIGH if item["field"] in ("apr", "interest_rate", "processing_fee") else RiskSeverity.MEDIUM,
                "field": item["field"],
                "value": "NOT_SPECIFIED",
                "status": "NOT_SPECIFIED",
                "evidence_id": None,
            })

        # 7. DOCUMENT CONFLICT
        for conf in conflicts:
            risks.append({
                "category": "DOCUMENT_CONFLICT",
                "title": f"Conflict in {conf.get('field', 'Loan Term').replace('_', ' ').title()}",
                "description": f"Conflicting terms found across documents: {conf.get('values')}",
                "severity": RiskSeverity.HIGH,
                "field": conf.get("field", "conflict"),
                "value": "Conflicting Values",
                "status": "MIXED",
                "evidence_id": None,
            })

        # 8. RATE RISK
        for fact in facts:
            if fact.category in ("interest_rate", "apr"):
                text_to_check = f"{fact.value} {fact.condition} {fact.source_text}".lower()
                if any(w in text_to_check for w in ("variable", "floating", "adjustable", "benchmark", "mclr", "sofr", "repo")):
                    risks.append({
                        "category": "RATE_RISK",
                        "title": "Variable / Floating Interest Rate",
                        "description": "Interest rate is floating or variable, meaning monthly payments may fluctuate with market rates.",
                        "severity": RiskSeverity.HIGH,
                        "field": fact.field,
                        "value": fact.value,
                        "status": fact.status.value,
                        "evidence_id": fact.source_chunk_id,
                    })

        return risks

    def calculate_risk_score(
        self,
        risk_factors: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Calculate deterministic risk score (0-100) and risk level:
        0–20   LOW
        21–40  MODERATE
        41–60  ELEVATED
        61–80  HIGH
        81–100 VERY HIGH
        """
        raw_score = 0
        categories_triggered = set()

        for rf in risk_factors:
            cat = rf.get("category")
            sev = rf.get("severity")
            categories_triggered.add(cat)

            if cat == "COST_RISK" and sev == RiskSeverity.HIGH:
                raw_score += self.weights.get("high_cost", 20)
            elif cat == "SCENARIO_SPECIFIC_RISK" and sev == RiskSeverity.HIGH:
                raw_score += self.weights.get("scenario_specific_penalty", 25)
            elif cat == "PENALTY_RISK" and sev == RiskSeverity.HIGH:
                raw_score += self.weights.get("late_payment_penalty", 15)
            elif cat == "DOCUMENT_CONFLICT":
                raw_score += self.weights.get("document_conflict", 20)
            elif cat == "RATE_RISK" and sev == RiskSeverity.HIGH:
                raw_score += self.weights.get("variable_rate", 10)
            elif cat == "INFORMATION_GAP" and sev == RiskSeverity.HIGH:
                raw_score += self.weights.get("missing_critical_information", 20)
            elif cat == "CONDITION_RISK":
                raw_score += self.weights.get("conditional_fee", 10)
            elif cat == "REPAYMENT_RISK" and sev in (RiskSeverity.HIGH, RiskSeverity.MEDIUM):
                raw_score += self.weights.get("prepayment_penalty", 20) * 0.5
            elif sev == RiskSeverity.MEDIUM:
                raw_score += 5
            elif sev == RiskSeverity.LOW:
                raw_score += 1

        score = max(0, min(100, int(raw_score)))

        if score <= 20:
            level = "LOW"
        elif score <= 40:
            level = "MODERATE"
        elif score <= 60:
            level = "ELEVATED"
        elif score <= 80:
            level = "HIGH"
        else:
            level = "VERY HIGH"

        return {
            "score": score,
            "level": level,
            "factors_count": len(risk_factors),
            "high_severity_count": sum(1 for rf in risk_factors if rf.get("severity") == RiskSeverity.HIGH),
            "medium_severity_count": sum(1 for rf in risk_factors if rf.get("severity") == RiskSeverity.MEDIUM),
            "low_severity_count": sum(1 for rf in risk_factors if rf.get("severity") == RiskSeverity.LOW),
        }

risk_engine = RiskEngine()
