from app.hilt.task_manager import HILTManager
from typing import Dict, Any, List

def escalate_to_hilt(query: str, product_ids: List[str]) -> Dict[str, Any]:
    """
    When confidence is low, escalate to HILT.
    This will create a task and return a pending response.
    """
    hilt_manager = HILTManager()
    
    # Create a HILT task
    task_id = hilt_manager.create_review_task(
        query=query,
        confidence=0.0,
        conflicts=[],
        product_ids=product_ids
    )
    
    return {
        "status": "hilt_pending",
        "task_id": task_id,
        "message": "Answer requires human review. We'll notify you when it's resolved."
    }

def continue_with_resolution(task_id: str, resolution_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    After HILT resolution, continue the RAG pipeline with human input.
    """
    hilt_manager = HILTManager()
    resolved = hilt_manager.resolve_review_task(task_id, resolution_data)
    
    if not resolved:
        return {"status": "error", "message": "Failed to resolve task"}
    
    return {
        "status": "resolved",
        "answer": resolution_data.get("answer", "Answer provided by human expert."),
        "confidence_score": 1.0,
        "confidence_label": "High (Human Verified)"
    }