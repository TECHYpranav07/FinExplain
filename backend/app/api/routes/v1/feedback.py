from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.db.repositories.feedback_repo import store_feedback
from app.auth.jwt_handler import get_current_user

router = APIRouter()

class FeedbackRequest(BaseModel):
    query: str
    answer: str
    is_correct: bool
    correction: Optional[str] = None

@router.post("/")
async def submit_feedback(
    request: FeedbackRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> dict:
    """Submit user feedback to improve the system."""
    user_id = current_user["id"]
    result = store_feedback(
        user_id=user_id,
        query=request.query,
        answer=request.answer,
        is_correct=request.is_correct,
        correction=request.correction
    )
    return {"status": "success", "feedback_id": result.get("id")}

