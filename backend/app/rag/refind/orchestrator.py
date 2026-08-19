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
    
    best_result = None
    best_confidence = 0.0
    
    strategies = [
        {"name": "default", "params": {}},
        {"name": "expand_query", "params": {"expand": True}},
        {"name": "relax_filters", "params": {"relax_date": True}}
    ]
    
    for attempt, strategy in enumerate(strategies):
        if attempt >= max_attempts:
            break
            
        print(f"[Refind] Attempt {attempt+1}: Using strategy '{strategy['name']}'")
        
        modified_question = question
        modified_product_ids = product_ids.copy()
        
        if strategy["name"] == "expand_query":
            modified_question = question + " fee interest rate penalty terms"
        elif strategy["name"] == "relax_filters":
            pass
        
        result = process_query(modified_question, modified_product_ids)
        confidence = result.get("confidence_score", 0.0)
        print(f"   -> Confidence: {confidence:.2f}")
        
        if confidence > best_confidence:
            best_confidence = confidence
            best_result = result
        
        if confidence >= 0.75:
            print("[Refind] High confidence threshold met. Returning answer.")
            return result
    
    if best_result:
        print(f"[Refind] Best confidence achieved: {best_confidence:.2f}")
        return best_result
    
    return {
        "answer": "Unable to retrieve relevant information. Please try rephrasing your question.",
        "confidence_score": 0.0,
        "confidence_label": "No Evidence",
        "citations": [],
        "retrieved_chunks": []
    }