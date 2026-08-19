from typing import Dict, Any, List
from app.tools.calculator import calculate_monthly_payment, calculate_total_cost
from app.tools.retrieval_tool import execute_retrieval_tool
from app.tools.verification_tool import execute_verification_tool

class FinancialAgentExecutor:
    """Dispatches tool execution based on classified tool intent."""
    
    @staticmethod
    def run_calculation(principal: float, annual_rate: float, tenure_months: int) -> Dict[str, Any]:
        emi = calculate_monthly_payment(principal, annual_rate, tenure_months)
        total = calculate_total_cost(principal, emi, tenure_months)
        return total

    @staticmethod
    def run_retrieval(query: str, product_ids: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        return execute_retrieval_tool(query, product_ids, top_k)

    @staticmethod
    def run_verification(answer: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        return execute_verification_tool(answer, chunks)

agent_executor = FinancialAgentExecutor()
