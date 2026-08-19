from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter()

@router.post("/")
async def submit_feedback(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "feedback_received", "id": 1}
