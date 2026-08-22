"""
Deterministic financial calculation engine for FinExplain.

All calculations are transparent: every result exposes its inputs,
formula, source evidence, and any missing/unknown components.

The LLM must NEVER perform these calculations itself.
"""

import math
from typing import Dict, Any, List, Optional


# ---------------------------------------------------------------------------
# Core EMI / Amortisation (existing — preserved)
# ---------------------------------------------------------------------------

def calculate_monthly_payment(
    principal: float,
    annual_interest_rate: float,
    tenure_months: int,
) -> float:
    """Calculate EMI using standard amortization formula."""
    if tenure_months <= 0:
        raise ValueError("Tenure must be greater than 0.")
    if annual_interest_rate == 0:
        return principal / tenure_months

    monthly_rate = (annual_interest_rate / 100.0) / 12.0
    numerator = principal * monthly_rate * math.pow(1 + monthly_rate, tenure_months)
    denominator = math.pow(1 + monthly_rate, tenure_months) - 1
    return round(numerator / denominator, 2)


def calculate_total_cost(
    principal: float,
    monthly_payment: float,
    tenure_months: int,
    upfront_fees: float = 0.0,
) -> Dict[str, Any]:
    """Calculate total loan cost and total interest paid."""
    total_repayment = round((monthly_payment * tenure_months) + upfront_fees, 2)
    total_interest = round(total_repayment - principal, 2)
    return {
        "principal": principal,
        "monthly_payment": monthly_payment,
        "tenure_months": tenure_months,
        "upfront_fees": upfront_fees,
        "total_interest": total_interest,
        "total_cost": total_repayment,
    }


# ---------------------------------------------------------------------------
# Transparent individual calculations
# ---------------------------------------------------------------------------

def calculate_processing_fee(
    principal: float,
    fee_rate: Optional[float] = None,
    fee_fixed: Optional[float] = None,
    fee_type: str = "percent",
    evidence_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculate a processing / origination fee with full transparency.

    Parameters
    ----------
    principal : loan amount
    fee_rate : percentage fee (e.g. 2.0 for 2%)
    fee_fixed : fixed fee amount
    fee_type : "percent" | "fixed" | "both"
    evidence_id : chunk_id backing the fee value

    Returns
    -------
    Transparent result dict with inputs, formula, result, and unknowns.
    """
    result: Dict[str, Any] = {
        "type": "processing_fee",
        "inputs": {
            "principal": principal,
            "fee_rate": fee_rate,
            "fee_fixed": fee_fixed,
            "fee_type": fee_type,
        },
        "formula": "",
        "result": None,
        "evidence_ids": [evidence_id] if evidence_id else [],
        "unknown_inputs": [],
        "assumptions": [],
    }

    if fee_type == "percent":
        if fee_rate is None:
            result["unknown_inputs"].append("fee_rate")
            return result
        rate_str = f"{int(fee_rate)}" if fee_rate == int(fee_rate) else f"{fee_rate}"
        amount = round(principal * (fee_rate / 100.0), 2)
        result["formula"] = f"{principal} * {rate_str}% = {amount}"
        result["result"] = amount
    elif fee_type == "fixed":
        if fee_fixed is None:
            result["unknown_inputs"].append("fee_fixed")
            return result
        result["formula"] = f"Fixed fee = {fee_fixed}"
        result["result"] = fee_fixed
    elif fee_type == "both":
        unknowns = []
        if fee_rate is None:
            unknowns.append("fee_rate")
        if fee_fixed is None:
            unknowns.append("fee_fixed")
        if unknowns:
            result["unknown_inputs"] = unknowns
            return result
        pct_amount = round(principal * (fee_rate / 100.0), 2)
        total = round(pct_amount + fee_fixed, 2)
        result["formula"] = f"{principal} × {fee_rate}% + {fee_fixed} = {total}"
        result["result"] = total
    else:
        result["unknown_inputs"].append("fee_type")

    return result


# ---------------------------------------------------------------------------
# Comprehensive loan scenario calculation
# ---------------------------------------------------------------------------

def calculate_loan_scenario(
    principal: Optional[float] = None,
    interest_rate: Optional[float] = None,
    apr: Optional[float] = None,
    tenure: Optional[int] = None,
    repayment_period: Optional[str] = None,
    processing_fee: Optional[float] = None,
    processing_fee_type: str = "percent",
    fixed_fees: Optional[float] = None,
    early_repayment_fee: Optional[float] = None,
    late_fee: Optional[float] = None,
    conditions: Optional[List[str]] = None,
    evidence_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Full loan scenario calculation with complete transparency.

    If ANY required input is missing, it is returned as an unknown cost —
    **never invented**.

    Returns
    -------
    ::

        {
            "inputs": { ... },
            "formula": "...",
            "results": { ... },
            "known_costs": [ ... ],
            "unknown_costs": [ ... ],
            "assumptions": [ ... ],
            "evidence_ids": [ ... ],
        }
    """
    inputs = {
        "principal": principal,
        "interest_rate": interest_rate,
        "apr": apr,
        "tenure_months": tenure,
        "repayment_period": repayment_period,
        "processing_fee_rate": processing_fee,
        "processing_fee_type": processing_fee_type,
        "fixed_fees": fixed_fees,
        "early_repayment_fee": early_repayment_fee,
        "late_fee": late_fee,
        "conditions": conditions or [],
    }

    known_costs: List[Dict[str, Any]] = []
    unknown_costs: List[str] = []
    assumptions: List[str] = []
    results: Dict[str, Any] = {}
    formulas: List[str] = []

    # --- Processing fee ---
    if processing_fee is not None and principal is not None:
        if processing_fee_type == "percent":
            pf_amount = round(principal * (processing_fee / 100.0), 2)
            formulas.append(f"Processing fee: {principal} × {processing_fee}% = {pf_amount}")
            known_costs.append({"item": "processing_fee", "amount": pf_amount})
            results["processing_fee_amount"] = pf_amount
        elif processing_fee_type == "fixed":
            known_costs.append({"item": "processing_fee", "amount": processing_fee})
            results["processing_fee_amount"] = processing_fee
    elif processing_fee is None:
        unknown_costs.append("processing_fee")

    # --- Fixed fees ---
    if fixed_fees is not None:
        known_costs.append({"item": "fixed_fees", "amount": fixed_fees})
        results["fixed_fees"] = fixed_fees
    elif fixed_fees is None:
        unknown_costs.append("fixed_fees")

    # --- EMI calculation ---
    if principal is not None and interest_rate is not None and tenure is not None:
        try:
            emi = calculate_monthly_payment(principal, interest_rate, tenure)
            total_repayment = round(emi * tenure, 2)
            total_interest = round(total_repayment - principal, 2)

            formulas.append(
                f"EMI: P×r×(1+r)^n / ((1+r)^n - 1) where P={principal}, "
                f"r={interest_rate}%/12, n={tenure} → EMI = {emi}"
            )
            results["emi"] = emi
            results["total_repayment"] = total_repayment
            results["total_interest"] = total_interest
            known_costs.append({"item": "total_interest", "amount": total_interest})
        except Exception:
            unknown_costs.append("emi_calculation")
    else:
        if principal is None:
            unknown_costs.append("principal")
        if interest_rate is None:
            unknown_costs.append("interest_rate")
        if tenure is None:
            unknown_costs.append("tenure")

    # --- Upfront total ---
    upfront = sum(
        c["amount"] for c in known_costs if c["item"] in ("processing_fee", "fixed_fees")
    )
    results["total_upfront_fees"] = round(upfront, 2)

    # --- Early repayment / late fee ---
    # FIN-029: Collect these BEFORE computing total_known_cost
    if early_repayment_fee is not None:
        known_costs.append({"item": "early_repayment_fee", "amount": early_repayment_fee})
    # FIN-029: Only mark as unknown if the scenario is relevant (not unconditionally)
    # early_repayment_fee and late_fee are situational — don't always list as unknown.

    if late_fee is not None:
        known_costs.append({"item": "late_fee", "amount": late_fee})

    # --- Total known cost (FIN-029: now computed AFTER all known costs collected) ---
    total_known = sum(c["amount"] for c in known_costs)
    results["total_known_cost"] = round(total_known, 2)

    return {
        "inputs": inputs,
        "formula": " | ".join(formulas) if formulas else "Insufficient inputs for calculation",
        "results": results,
        "known_costs": known_costs,
        "unknown_costs": unknown_costs,
        "assumptions": assumptions,
        "evidence_ids": evidence_ids or [],
    }


def calculate_early_repayment_penalty(
    penalty_rate: float,
    outstanding_principal: Optional[float] = None,
    original_principal: Optional[float] = None,
    lock_in_months: Optional[int] = None,
    current_month: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Calculate early repayment/foreclosure penalty with explicit principal distinction.

    CRITICAL RULE:
    Never assume original_principal == outstanding_principal unless explicitly proven.
    If outstanding_principal is missing, return formula and flag unknown.
    """
    result: Dict[str, Any] = {
        "type": "early_repayment_penalty",
        "penalty_rate": penalty_rate,
        "lock_in_months": lock_in_months,
        "is_waived": False,
        "formula": "",
        "result": None,
        "unknown_inputs": [],
        "notes": [],
    }

    # Check lock-in / waiver timing
    if lock_in_months and current_month:
        if current_month > lock_in_months:
            result["is_waived"] = True
            result["result"] = 0.0
            result["formula"] = f"Waiver applies after {lock_in_months} months (Current month: {current_month}) → ₹0 penalty"
            return result

    if outstanding_principal is not None:
        amount = round(outstanding_principal * (penalty_rate / 100.0), 2)
        result["formula"] = f"{outstanding_principal} × {penalty_rate}% = {amount}"
        result["result"] = amount
    else:
        result["unknown_inputs"].append("current_outstanding_principal")
        result["formula"] = f"{penalty_rate}% × [Current Outstanding Principal]"
        result["notes"].append(
            "Current outstanding principal is not specified in the documents. "
            "Original sanctioned loan amount cannot be used as outstanding balance without proof of 0 EMIs paid."
        )

    return result

