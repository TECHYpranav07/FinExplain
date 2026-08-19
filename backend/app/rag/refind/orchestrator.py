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
    
    # Define strategies: each is a dict with modifications to apply
    strategies = [
        {"name": "default", "params": {}},  # Attempt 1: Default
        {"name": "expand_query", "params": {"expand": True}},  # Attempt 2: Expand
        {"name": "relax_filters", "params": {"relax_date": True}}  # Attempt 3: Relax
    ]
    
    for attempt, strategy in enumerate(strategies):
        if attempt >= max_attempts:
            break
            
        print(f"🔄 Refind Attempt {attempt+1}: Using strategy '{strategy['name']}'")
        
        # Apply strategy modifications to the query or params
        modified_question = question
        modified_product_ids = product_ids.copy()
        
        if strategy["name"] == "expand_query":
            # Simple expansion: add synonyms or rephrase (advanced: use LLM later)
            # For now, just add a generic financial synonym to improve recall
            expanded_terms = [" fee ", " charge ", " rate ", " interest ", " penalty "]
            # We'll just leave it as is for now but flag it.
            # In production, use a small LLM call here.
            modified_question = question + " fee interest rate penalty"
            
        elif strategy["name"] == "relax_filters":
            # Relax date filters: we don't have strict date filtering yet,
            # but we could remove product-specific constraints if needed.
            # For now, we pass the same IDs but future implementations can ignore dates.
            pass
        
        # Run the main RAG pipeline with the modified parameters
        result = process_query(modified_question, modified_product_ids)
        
        confidence = result.get("confidence_score", 0.0)
        print(f"   → Confidence: {confidence:.2f}")
        
        # Track best result
        if confidence > best_confidence:
            best_confidence = confidence
            best_result = result
        
        # If confidence is high enough, return immediately
        if confidence >= 0.75:
            print("✅ Confidence threshold met. Returning answer.")
            return result
    
    # After all attempts, return the best result
    # (Even if low confidence, we return it; the frontend will see the label)
    if best_result:
        print(f"⚠️ Max attempts reached. Best confidence: {best_confidence:.2f}")
        return best_result
    
    # Fallback if something went terribly wrong
    return {
        "answer": "Unable to retrieve relevant information. Please try rephrasing your question.",
        "confidence_score": 0.0,
        "confidence_label": "No Evidence",
        "citations": [],
        "retrieved_chunks": []
    }