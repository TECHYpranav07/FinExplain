from typing import List, Dict, Any, Optional
from datetime import datetime
from app.db.supabase_client import get_supabase_client
from app.models.hilt_task import HiltTaskCreate, HILTStatus

class HiltTaskRepository:
    def __init__(self):
        self.table_name = "hilt_tasks"

    def create(self, task: HiltTaskCreate) -> Dict[str, Any]:
        client = get_supabase_client()
        data = task.model_dump()
        if isinstance(data.get("status"), HILTStatus):
            data["status"] = data["status"].value
        response = client.table(self.table_name).insert(data).execute()
        return response.data[0] if response.data else {}

    def get_by_id(self, task_id: int) -> Optional[Dict[str, Any]]:
        client = get_supabase_client()
        response = client.table(self.table_name).select("*").eq("id", task_id).execute()
        return response.data[0] if response.data else None

    def update_resolution(
        self, task_id: int, resolution_data: Dict[str, Any], resolver_user_id: int, status: HILTStatus = HILTStatus.RESOLVED
    ) -> Dict[str, Any]:
        client = get_supabase_client()
        update_payload = {
            "resolution_data": resolution_data,
            "resolver_user_id": resolver_user_id,
            "status": status.value if isinstance(status, HILTStatus) else status,
            "resolved_at": datetime.utcnow().isoformat()
        }
        response = client.table(self.table_name).update(update_payload).eq("id", task_id).execute()
        return response.data[0] if response.data else {}

hilt_repo = HiltTaskRepository()
