from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any
from app.db.repositories.hilt_repo import create_hilt_task, resolve_hilt_task
from app.auth.jwt_handler import get_current_user

router = APIRouter()

class HILTRequest(BaseModel):
    task_type: str
    payload: Dict[str, Any]

class HILTResolveRequest(BaseModel):
    resolution_data: Dict[str, Any]

@router.post("/tasks")
async def create_task(
    request: HILTRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a HILT task (e.g., for conflict resolution) scoped to the user."""
    user_id = current_user["id"]
    task = create_hilt_task(user_id, request.task_type, request.payload)
    return task

@router.post("/resolve/{task_id}")
async def resolve_task(
    task_id: str,
    request: HILTResolveRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Resolve a HILT task with human input."""
    result = resolve_hilt_task(task_id, request.resolution_data, resolver_user_id=current_user["id"])
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return result

