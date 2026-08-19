from app.workers.celery_app import celery_app
from app.db.repositories.hilt_repo import create_hilt_task, resolve_hilt_task
from typing import Dict, Any

@celery_app.task(bind=True)
def create_hilt_task_async(self, user_id: str, task_type: str, payload: Dict[str, Any]):
    """Asynchronously creates a HILT task in background."""
    try:
        return create_hilt_task(user_id=user_id, task_type=task_type, payload=payload)
    except Exception as e:
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise

@celery_app.task(bind=True)
def resolve_hilt_task_async(self, task_id: str, resolution_data: Dict[str, Any]):
    """Asynchronously marks a HILT task as resolved."""
    try:
        return resolve_hilt_task(task_id=task_id, resolution_data=resolution_data)
    except Exception as e:
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise
