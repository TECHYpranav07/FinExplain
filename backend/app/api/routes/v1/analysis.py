"""
Proactive analysis endpoints for FinExplain.

- POST /review     — Proactive loan review for a product
- POST /before-confirmation — "Before You Confirm" checklist
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List

from app.api.schemas import (
    LoanReviewRequest,
    LoanReviewResponse,
    BeforeConfirmationRequest,
    BeforeConfirmationResponse,
)
from app.db.repositories.product_repo import get_product_by_id
from app.rag.retrieval.hybrid_retriever import hybrid_search
from app.rag.retrieval.reranker import rerank_chunks
from app.rag.extraction.fact_extractor import extract_structured_facts
from app.rag.extraction.condition_detector import annotate_facts_with_conditions
from app.rag.extraction.missing_detector import detect_missing_information
from app.rag.extraction.cost_driver_detector import detect_cost_drivers
from app.rag.extraction.loan_analyzer import (
    analyze_loan_document,
    generate_before_confirmation_checklist,
    prioritize_cost_drivers,
)
from app.rag.verification.conflict_detector import detect_fact_conflicts
from app.rag.generation.generator import generate_loan_review, generate_before_confirmation

router = APIRouter()


def _extract_facts_for_products(product_ids: List[str]) -> Dict[str, Any]:
    """
    Shared helper: retrieve chunks, extract facts, detect conditions/missing/conflicts.
    """
    # Retrieve all relevant chunks via a broad query
    all_chunks = hybrid_search(
        query="loan terms fees charges conditions eligibility repayment penalty waiver",
        product_ids=product_ids,
        top_k=50,
    )

    if not all_chunks:
        raise HTTPException(
            status_code=404,
            detail="No document chunks found for the specified products.",
        )

    # Rerank for relevance
    reranked = rerank_chunks(
        query="loan terms fees charges conditions eligibility",
        chunks=all_chunks,
        top_k=20,
    )

    # Extract structured facts
    product_name = reranked[0].get("product_name", "") if reranked else ""
    document_name = reranked[0].get("document_name", "") if reranked else ""
    facts = extract_structured_facts(reranked, product_name=product_name, document_name=document_name)
    facts = annotate_facts_with_conditions(facts, reranked)

    # Detect missing information
    missing = detect_missing_information(facts)

    # Detect conflicts
    conflicts = detect_fact_conflicts(facts)

    # Detect cost drivers
    cost_drivers = detect_cost_drivers(facts)
    prioritized = prioritize_cost_drivers(facts)

    return {
        "facts": facts,
        "missing": missing,
        "conflicts": conflicts,
        "cost_drivers": cost_drivers,
        "prioritized_drivers": prioritized,
        "chunks": reranked,
    }


@router.post("/review", response_model=LoanReviewResponse)
async def loan_review(request: LoanReviewRequest) -> Dict[str, Any]:
    """
    Proactive loan document review.

    Automatically identifies important terms, cost drivers, penalties,
    conditions, missing information, and conflicts for the specified products.
    """
    # Verify products exist
    for pid in request.product_ids:
        product = get_product_by_id(pid)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {pid} not found.")

    extracted = _extract_facts_for_products(request.product_ids)

    # Build structured review
    review = analyze_loan_document(
        facts=extracted["facts"],
        missing=extracted["missing"],
        conflicts=extracted["conflicts"],
        cost_drivers=extracted["cost_drivers"],
    )

    # Generate natural-language review
    facts_dicts = [f.model_dump() for f in extracted["facts"]]
    review_text_result = generate_loan_review(
        structured_facts=facts_dicts,
        missing_information=extracted["missing"],
        conflicts=extracted["conflicts"],
        cost_drivers=extracted["cost_drivers"],
    )

    return {
        "review": review,
        "review_text": review_text_result.get("review"),
        "checklist": None,
        "cost_drivers": extracted["prioritized_drivers"],
    }


@router.post("/before-confirmation", response_model=BeforeConfirmationResponse)
async def before_confirmation(request: BeforeConfirmationRequest) -> Dict[str, Any]:
    """
    "Before You Confirm" checklist.

    Identifies the most important things a borrower should understand
    before committing to a loan, with evidence attached to every item.
    """
    # Verify products exist
    for pid in request.product_ids:
        product = get_product_by_id(pid)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {pid} not found.")

    extracted = _extract_facts_for_products(request.product_ids)

    # Build checklist
    checklist = generate_before_confirmation_checklist(
        facts=extracted["facts"],
        missing=extracted["missing"],
        conflicts=extracted["conflicts"],
    )

    # Generate natural-language checklist
    facts_dicts = [f.model_dump() for f in extracted["facts"]]
    checklist_text_result = generate_before_confirmation(
        structured_facts=facts_dicts,
        missing_information=extracted["missing"],
        conflicts=extracted["conflicts"],
    )

    return {
        "checklist": checklist,
        "checklist_text": checklist_text_result.get("checklist"),
    }
