from app.db.supabase_client import get_supabase_client
from typing import Dict, Any, Optional
import uuid
from datetime import datetime

def create_hilt_task(
    user_id: str,
    task_type: str,
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a new HILT task."""
    supabase = get_supabase_client()
    data = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "task_type": task_type,
        "payload": payload,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    }
    response = supabase.table("hilt_tasks").insert(data).execute()
    return response.data[0] if response.data else None

def resolve_hilt_task(task_id: str, resolution_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve a HILT task with human input."""
    supabase = get_supabase_client()
    update_data = {
        "status": "resolved",
        "resolution_data": resolution_data,
        "resolved_at": datetime.utcnow().isoformat()
    }
    response = supabase.table("hilt_tasks").update(update_data).eq("id", task_id).execute()
    return response.data[0] if response.data else None