from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Dict, Any
import os

# Import the sync pipeline (fallback if Celery is not configured)
from app.ingestion.pipeline import process_document

# Import the async Celery task (optional – only if Celery is set up)
try:
    from app.workers.ingestion_tasks import process_document_async
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

router = APIRouter()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    product_id: str = Form(...),
    use_async: bool = Form(False)  # Optional flag to use Celery
) -> Dict[str, Any]:
    """
    Upload a loan document (PDF) and trigger the ingestion pipeline.
    If use_async=True and Celery is available, the ingestion runs in the background.
    Otherwise, it runs synchronously (blocking).
    """
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        # Read file bytes
        file_bytes = await file.read()
        
        # Option 1: Use Celery async task
        if use_async and CELERY_AVAILABLE:
            task = process_document_async.delay(
                file_bytes=file_bytes,
                file_name=file.filename,
                product_id=product_id
            )
            return {
                "status": "processing",
                "task_id": task.id,
                "message": "Document queued for background ingestion."
            }
        
        # Option 2: Synchronous processing (blocking, but immediate)
        result = process_document(
            file_bytes=file_bytes,
            file_name=file.filename,
            product_id=product_id
        )
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))