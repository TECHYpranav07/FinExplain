from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Dict, Any
from app.ingestion.pipeline import process_document

# ✅ Must have this line
router = APIRouter()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    product_id: str = Form(...),
) -> Dict[str, Any]:
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        file_bytes = await file.read()
        result = process_document(
            file_bytes=file_bytes,
            file_name=file.filename,
            product_id=product_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))