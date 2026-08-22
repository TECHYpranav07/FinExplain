import asyncio
import os
import logging
from typing import Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from app.auth.jwt_handler import get_current_user
from app.db.repositories.product_repo import get_product_by_id
from app.core.config import settings

# Import the sync pipeline
from app.ingestion.pipeline import process_document

# Import the async Celery task (optional – only if Celery is set up)
try:
    from app.workers.ingestion_tasks import process_document_async
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

from app.db.repositories.document_repo import (
    get_documents_by_user,
    get_document_by_id,
    delete_document_by_id,
)

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


@router.get("/")
def list_user_documents(current_user: Dict[str, Any] = Depends(get_current_user)):
    """List all documents for products owned by the authenticated user."""
    return get_documents_by_user(current_user["id"])


@router.get("/{document_id}")
def get_document(document_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieve document details by ID."""
    doc = get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{document_id}")
def delete_document(document_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Delete a document by ID."""
    doc = get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    success = delete_document_by_id(document_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete document")
    return {"message": "Document deleted successfully"}


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    product_id: str = Form(...),
    use_async: bool = Form(False),  # Optional flag to use Celery
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Upload a loan document (PDF) and trigger the ingestion pipeline.
    Ensures the target product belongs to the authenticated user.
    FIN-030: Validates file type (case-insensitive), %PDF magic bytes, and 50MB size limit.
    FIN-031: Runs synchronous pipeline off the event loop via asyncio.to_thread.
    """
    # Verify product ownership
    product = get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product with ID '{product_id}' not found.")

    is_sample = product_id in ("1", "2") and settings.is_development
    if not is_sample and product.get("user_id") and product.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied: You do not own this product.")

    user_id = current_user["id"]

    # Validate filename and extension (case-insensitive)
    raw_filename = file.filename or "uploaded_document.pdf"
    safe_filename = os.path.basename(raw_filename)
    if not safe_filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed (.pdf extension required)")

    try:
        # Read file bytes with size constraint
        file_bytes = await file.read()
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes)")
        if len(file_bytes) > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail=f"File exceeds maximum allowed size of 50 MB (size: {len(file_bytes) / 1024 / 1024:.1f} MB)")

        # Validate PDF magic bytes (%PDF)
        if not file_bytes.startswith(b"%PDF"):
            raise HTTPException(status_code=400, detail="Invalid PDF content: file header does not match %PDF signature")

        # Option 1: Use Celery async task
        if use_async and CELERY_AVAILABLE:
            task = process_document_async.delay(
                file_bytes=file_bytes,
                file_name=safe_filename,
                product_id=product_id
            )
            return {
                "status": "processing",
                "task_id": task.id,
                "message": "Document queued for background ingestion."
            }

        # Option 2: Synchronous processing (offloaded to thread to avoid blocking event loop)
        result = await asyncio.to_thread(
            process_document,
            file_bytes=file_bytes,
            file_name=safe_filename,
            product_id=product_id,
            user_id=user_id
        )
        return result

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Validation error in document upload: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing document {safe_filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred during document processing. Please check the document format and try again.")