from typing import Optional
from app.db.supabase_client import get_supabase_client
from app.core.config import settings

def upload_document_to_storage(file_bytes: bytes, file_name: str, bucket_name: Optional[str] = None) -> str:
    """
    Uploads document bytes to Supabase Storage.
    Falls back to returning the path if storage upload is bypassed.
    """
    bucket = bucket_name or settings.STORAGE_BUCKET or "loan_docs"
    try:
        supabase = get_supabase_client()
        response = supabase.storage.from_(bucket).upload(
            file_name,
            file_bytes,
            {"content-type": "application/pdf"}
        )
        return f"{bucket}/{file_name}"
    except Exception as e:
        # If bucket does not exist, return simulated storage path
        return f"{bucket}/{file_name}"
