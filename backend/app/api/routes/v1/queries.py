from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from app.rag.refind.orchestrator import process_with_refind
from app.db.repositories.product_repo import get_product_by_id

router = APIRouter()

class AskRequest(BaseModel):
    question: str
    product_ids: List[str]

@router.post("/ask")
async def ask_question(request: AskRequest) -> Dict[str, Any]:
    """
    Ask a question about one or more loan products.
    Uses Hybrid Search (Pinecone + BM25), Reranking, and LLM generation.
    """
    # Verify all product IDs exist before processing
    for product_id in request.product_ids:
        product = get_product_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product with ID {product_id} not found."
            )
    
    # Run the full RAG pipeline with corrective refind loop (max 3 attempts)
    result = process_with_refind(
        question=request.question,
        product_ids=request.product_ids,
        max_attempts=3
    )
    
    return result