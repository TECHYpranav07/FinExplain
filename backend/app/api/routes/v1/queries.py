import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from app.rag.orchestrator import process_query
from app.db.repositories.product_repo import get_product_by_id

logger = logging.getLogger(__name__)
router = APIRouter()

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    product_ids: List[str] = Field(default_factory=list)

@router.post("/ask")
async def ask_question(request: AskRequest) -> Dict[str, Any]:
    """
    Ask a question about one or more loan products.
    Uses Evidence-First RAG: Retrieval -> Extraction -> Verification -> Scoring.
    """
    try:
        # Verify product IDs if specified
        for product_id in request.product_ids:
            if product_id in ("1", "2"):
                continue
            product = get_product_by_id(product_id)
            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product with ID '{product_id}' not found. Please upload a document or use product ID '1'."
                )
        
        # Run the evidence-first RAG pipeline
        result = process_query(
            question=request.question,
            product_ids=request.product_ids
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing ask query: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error in RAG pipeline: {str(e)}"
        )
