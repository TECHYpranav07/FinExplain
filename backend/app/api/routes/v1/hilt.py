from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from app.db.repositories.hilt_repo import create_hilt_task, resolve_hilt_task
from app.core.constants import DEFAULT_DEMO_USER_ID

router = APIRouter()

class HILTRequest(BaseModel):
    task_type: str
    payload: Dict[str, Any]

class HILTResolveRequest(BaseModel):
    resolution_data: Dict[str, Any]

@router.post("/tasks")
async def create_task(request: HILTRequest) -> Dict[str, Any]:
    """Create a HILT task (e.g., for conflict resolution)."""
    # For testing, use a fixed user ID
    user_id = DEFAULT_DEMO_USER_ID
    task = create_hilt_task(user_id, request.task_type, request.payload)
    return task

@router.post("/resolve/{task_id}")
async def resolve_task(task_id: str, request: HILTResolveRequest) -> Dict[str, Any]:
    """Resolve a HILT task with human input."""
    result = resolve_hilt_task(task_id, request.resolution_data)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return result
