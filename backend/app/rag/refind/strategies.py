from typing import Dict, Any, List
from app.rag.enhancement.hyde_generator import generate_hypothetical_document
from app.rag.enhancement.query_rewriter import rewrite_query

class RefindStrategy:
    """Strategy interface for corrective retrieval."""
    def apply(self, query: str, product_ids: List[str]) -> Dict[str, Any]:
        raise NotImplementedError

class DefaultStrategy(RefindStrategy):
    def apply(self, query: str, product_ids: List[str]) -> Dict[str, Any]:
        return {"query": query, "product_ids": product_ids, "strategy_name": "default"}

class QueryExpansionStrategy(RefindStrategy):
    def apply(self, query: str, product_ids: List[str]) -> Dict[str, Any]:
        expanded = rewrite_query(query, intent="lookup")
        return {"query": expanded, "product_ids": product_ids, "strategy_name": "query_expansion"}

class HyDEStrategy(RefindStrategy):
    def apply(self, query: str, product_ids: List[str]) -> Dict[str, Any]:
        hyde_doc = generate_hypothetical_document(query)
        return {"query": f"{query} {hyde_doc[:150]}", "product_ids": product_ids, "strategy_name": "hyde"}

def get_strategy(strategy_name: str) -> RefindStrategy:
    strategies = {
        "default": DefaultStrategy(),
        "expand_query": QueryExpansionStrategy(),
        "hyde": HyDEStrategy()
    }
    return strategies.get(strategy_name, DefaultStrategy())
