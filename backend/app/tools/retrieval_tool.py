from typing import List, Dict, Any
from app.rag.retrieval.hybrid_retriever import hybrid_search
from app.rag.retrieval.reranker import rerank_chunks

def execute_retrieval_tool(query: str, product_ids: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
    """Tool invocation for agent retrieval."""
    raw_chunks = hybrid_search(query=query, product_ids=product_ids, top_k=20)
    reranked = rerank_chunks(query=query, chunks=raw_chunks, top_k=top_k)
    return reranked
