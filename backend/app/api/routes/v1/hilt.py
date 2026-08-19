from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter()

@router.post("/resolve")
async def resolve_hilt_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"task_id": payload.get("task_id"), "status": "resolved"}

@router.post("/confirm")
async def confirm_hilt_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"task_id": payload.get("task_id"), "status": "confirmed"}
