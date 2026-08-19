from typing import List, Dict, Any
from app.evaluation.metrics import compute_mrr, compute_recall_at_k, compute_citation_precision

class RAGEvaluator:
    """Evaluates RAG pipeline outputs against golden standard datasets."""
    
    @staticmethod
    def evaluate_query(
        rag_output: Dict[str, Any],
        expected_chunk_ids: List[str]
    ) -> Dict[str, Any]:
        retrieved_ids = [c.get("id") for c in rag_output.get("retrieved_chunks", [])]
        citations = rag_output.get("citations", [])
        
        mrr = compute_mrr(retrieved_ids, expected_chunk_ids)
        recall_5 = compute_recall_at_k(retrieved_ids, expected_chunk_ids, k=5)
        citation_p = compute_citation_precision(citations)
        
        return {
            "mrr": mrr,
            "recall@5": recall_5,
            "citation_precision": citation_p,
            "confidence_score": rag_output.get("confidence_score", 0.0),
            "passed": recall_5 >= 0.8 and citation_p >= 0.75
        }

rag_evaluator = RAGEvaluator()
