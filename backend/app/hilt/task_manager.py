from app.db.repositories.hilt_repo import create_hilt_task, resolve_hilt_task
from typing import Dict, Any, List
import json

class HILTManager:
    def __init__(self, user_id: str = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"):
        self.user_id = user_id

    def create_review_task(self, query: str, confidence: float, conflicts: List[Dict], product_ids: List[str]) -> str:
        """Create a HILT task for manual review."""
        payload = {
            "query": query,
            "confidence": confidence,
            "conflicts": conflicts,
            "product_ids": product_ids,
            "status": "pending"
        }
        task = create_hilt_task(
            user_id=self.user_id,
            task_type="manual_review",
            payload=payload
        )
        return task.get("id")

    def resolve_review_task(self, task_id: str, resolution: Dict[str, Any]) -> bool:
        """Resolve a HILT task with human input."""
        result = resolve_hilt_task(task_id, resolution)
        return result is not None

    def should_trigger_hilt(self, confidence: float, conflicts: List) -> bool:
        """Check if HILT should be triggered."""
        return confidence < 0.4 or len(conflicts) > 0