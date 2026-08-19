from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.db.repositories.feedback_repo import store_feedback

router = APIRouter()

class FeedbackRequest(BaseModel):
    query: str
    answer: str
    is_correct: bool
    correction: Optional[str] = None

@router.post("/")
async def submit_feedback(request: FeedbackRequest) -> dict:
    """Submit user feedback to improve the system."""
    user_id = "test-user-123"
    result = store_feedback(
        user_id=user_id,
        query=request.query,
        answer=request.answer,
        is_correct=request.is_correct,
        correction=request.correction
    )
    return {"status": "success", "feedback_id": result.get("id")}