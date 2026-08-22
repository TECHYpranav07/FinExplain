import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from app.rag.orchestrator import process_query
from app.db.repositories.product_repo import get_product_by_id
from app.auth.jwt_handler import get_current_user
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    product_ids: List[str] = Field(default_factory=list)

@router.post("/ask")
async def ask_question(
    request: AskRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Ask a question about one or more loan products belonging to the user.
    Uses Evidence-First RAG: Retrieval -> Extraction -> Verification -> Scoring.
    FIN-031: Runs synchronous pipeline off the event loop using asyncio.to_thread.
    """
    try:
        user_id = current_user["id"]

        # Verify product IDs if specified and ensure ownership
        for product_id in request.product_ids:
            if product_id in ("1", "2") and settings.is_development:
                continue
            product = get_product_by_id(product_id)
            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product with ID '{product_id}' not found. Please upload a document or select an existing product."
                )
            if product.get("user_id") and product.get("user_id") != user_id:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied: Product '{product.get('name', product_id)}' does not belong to your account."
                )
        
        # Run the evidence-first RAG pipeline asynchronously in worker thread
        result = await asyncio.to_thread(
            process_query,
            question=request.question,
            product_ids=request.product_ids,
            user_id=user_id
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing ask query: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your query. Please verify that the system dependencies and API keys are configured."
        )
