from typing import List, Dict, Any, Optional
from app.db.supabase_client import get_supabase_client
from app.models.verified_answer import VerifiedAnswerCreate

class VerifiedAnswerRepository:
    def __init__(self):
        self.table_name = "verified_answers"

    def create(self, answer: VerifiedAnswerCreate) -> Dict[str, Any]:
        client = get_supabase_client()
        response = client.table(self.table_name).insert(answer.model_dump()).execute()
        return response.data[0] if response.data else {}

    def get_by_id(self, answer_id: str) -> Optional[Dict[str, Any]]:
        client = get_supabase_client()
        response = client.table(self.table_name).select("*").eq("id", answer_id).execute()
        return response.data[0] if response.data else None

    def search_by_query(self, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        client = get_supabase_client()
        response = client.table(self.table_name).select("*").ilike("user_query", f"%{query_text}%").limit(limit).execute()
        return response.data or []

verified_answer_repo = VerifiedAnswerRepository()
