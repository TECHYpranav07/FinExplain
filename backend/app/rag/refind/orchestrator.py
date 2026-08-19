from app.rag.orchestrator import process_query
from typing import Dict, Any, List

def process_with_refind(
    question: str,
    product_ids: List[str],
    max_attempts: int = 3
) -> Dict[str, Any]:
    """
    Runs the RAG pipeline with a corrective loop.
    If confidence < 0.75, attempts alternative retrieval strategies.
    """
    
    # Define refind strategies
    strategies = [
        {"name": "default", "params": {}},
        {"name": "expand_query", "params": {"expand": True}},  # TODO: implement expansion
        {"name": "relax_metadata", "params": {"relax_date": True}},  # TODO: implement
        {"name": "flip_weights", "params": {"dense_weight": 0.3, "sparse_weight": 0.7}}
    ]
    
    best_result = None
    best_confidence = 0.0
    
    for attempt in range(max_attempts):
        strategy = strategies[attempt] if attempt < len(strategies) else strategies[-1]
        
        # For now, just call the default processor
        # In the future, pass strategy params to modify retrieval
        result = process_query(question, product_ids)
        
        confidence = result.get("confidence_score", 0.0)
        
        # Track best result
        if confidence > best_confidence:
            best_confidence = confidence
            best_result = result
        
        # If confidence is high enough, return immediately
        if confidence >= 0.75:
            return result
    
    # After all attempts, return the best result
    # Even if low confidence, we return it (will be handled by HILT)
    return best_result