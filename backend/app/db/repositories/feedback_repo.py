from app.db.supabase_client import get_supabase_client
from typing import Dict, Any
import uuid
from datetime import datetime

def store_feedback(
    user_id: str,
    query: str,
    answer: str,
    is_correct: bool,
    correction: str = None
) -> Dict[str, Any]:
    """Store user feedback for future improvement."""
    supabase = get_supabase_client()
    data = {
        "id": str(uuid.uuid4()),
        "user_query": query,
        "final_answer": answer,
        "verified_by_user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
        # We'll store correction as a JSON field if provided
        # Schema doesn't have this exact field, so we adapt to verified_answers table
        # Let's map it to existing columns
        "source_citations": {"user_feedback": correction} if correction else {},
        "confidence_score": 1.0 if is_correct else 0.0
    }
    # Use the verified_answers table
    response = supabase.table("verified_answers").insert(data).execute()
    return response.data[0] if response.data else None