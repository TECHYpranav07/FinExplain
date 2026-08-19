from typing import Dict, Any, Optional
from datetime import datetime
from app.db.supabase_client import get_supabase_client

def apply_resolution(task_id: str, resolution_data: Dict[str, Any], resolver_user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Applies human verification and creates a verified_answers entry to train/evaluate future retrievals.
    """
    supabase = get_supabase_client()
    
    # 1. Update task status
    update_payload = {
        "status": "resolved",
        "resolution_data": resolution_data,
        "resolved_at": datetime.utcnow().isoformat()
    }
    task_res = supabase.table("hilt_tasks").update(update_payload).eq("id", task_id).execute()
    
    # 2. Optionally store into verified_answers
    query = resolution_data.get("query", "")
    answer = resolution_data.get("answer", "")
    if query and answer:
        verified_payload = {
            "user_query": query,
            "final_answer": answer,
            "confidence_score": 1.0,
            "source_citations": resolution_data.get("citations", []),
            "created_at": datetime.utcnow().isoformat()
        }
        if resolver_user_id:
            verified_payload["verified_by_user_id"] = resolver_user_id
        supabase.table("verified_answers").insert(verified_payload).execute()
        
    return task_res.data[0] if task_res.data else {}
