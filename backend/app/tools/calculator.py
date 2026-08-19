import math
from typing import Dict, Any

def calculate_monthly_payment(principal: float, annual_interest_rate: float, tenure_months: int) -> float:
    """Calculate EMI using standard amortization formula."""
    if tenure_months <= 0:
        raise ValueError("Tenure must be greater than 0.")
    if annual_interest_rate == 0:
        return principal / tenure_months

    monthly_rate = (annual_interest_rate / 100.0) / 12.0
    numerator = principal * monthly_rate * math.pow(1 + monthly_rate, tenure_months)
    denominator = math.pow(1 + monthly_rate, tenure_months) - 1
    return round(numerator / denominator, 2)

def calculate_total_cost(principal: float, monthly_payment: float, tenure_months: int, upfront_fees: float = 0.0) -> Dict[str, Any]:
    """Calculate total loan cost and total interest paid."""
    total_repayment = round((monthly_payment * tenure_months) + upfront_fees, 2)
    total_interest = round(total_repayment - principal, 2)
    return {
        "principal": principal,
        "monthly_payment": monthly_payment,
        "tenure_months": tenure_months,
        "upfront_fees": upfront_fees,
        "total_interest": total_interest,
        "total_cost": total_repayment
    }
