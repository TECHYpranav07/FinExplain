from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List

from app.api.schemas import (
    LoanReviewRequest,
    LoanReviewResponse,
    BeforeConfirmationRequest,
    BeforeConfirmationResponse,
    LoanCompareRequest,
    LoanCompareResponse,
)
from app.db.repositories.product_repo import get_product_by_id
from app.auth.jwt_handler import get_current_user
from app.core.config import settings
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
from app.tools.comparator import compare_loan_facts
from app.rag.verification.conflict_detector import detect_fact_conflicts
from app.rag.generation.generator import (
    generate_loan_review,
    generate_before_confirmation,
    generate_loan_comparison,
)

router = APIRouter()


def _extract_facts_for_products(product_ids: List[str], user_id: str = None) -> Dict[str, Any]:
    """
    Shared helper: retrieve chunks, extract facts, detect conditions/missing/conflicts.
    """
    # Retrieve all relevant chunks via a broad query filtered by user_id
    all_chunks = hybrid_search(
        query="loan terms fees charges conditions eligibility repayment penalty waiver",
        product_ids=product_ids,
        top_k=50,
        user_id=user_id,
    )

    if not all_chunks:
        from app.db.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        docs_count = 0
        if supabase:
            try:
                doc_res = supabase.table("documents").select("id").in_("product_id", product_ids).execute()
                docs_count = len(doc_res.data or [])
            except Exception:
                docs_count = 0

        if docs_count == 0:
            raise HTTPException(
                status_code=404,
                detail="No documents have been uploaded for the selected loan product yet. Please go to Documents to upload and index your loan agreement PDF first.",
            )
        else:
            raise HTTPException(
                status_code=404,
                detail="No indexed document clauses could be retrieved for this product. Please ensure the document ingestion finished successfully in the Documents section.",
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
async def loan_review(
    request: LoanReviewRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Proactive loan document review scoped to user's products.

    Automatically identifies important terms, cost drivers, penalties,
    conditions, missing information, and conflicts for the specified products.
    """
    user_id = current_user["id"]
    # Verify products exist and belong to user
    for pid in request.product_ids:
        if pid in ("1", "2") and settings.is_development:
            continue
        product = get_product_by_id(pid)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {pid} not found.")
        if product.get("user_id") and product.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail=f"Access denied to product {pid}.")

    extracted = _extract_facts_for_products(request.product_ids, user_id=user_id)

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

    # Generate actionable checklist with ✓ / ⚠ / ? markers
    checklist = generate_before_confirmation_checklist(
        facts=extracted["facts"],
        missing=extracted["missing"],
        conflicts=extracted["conflicts"],
    )

    return {
        "review": review,
        "review_text": review_text_result.get("review"),
        "checklist": checklist,
        "cost_drivers": extracted["prioritized_drivers"],
    }


@router.post("/before-confirmation", response_model=BeforeConfirmationResponse)
async def before_confirmation(
    request: BeforeConfirmationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    "Before You Confirm" checklist scoped to user's products.

    Identifies the most important things a borrower should understand
    before committing to a loan, with evidence attached to every item.
    """
    user_id = current_user["id"]
    # Verify products exist and belong to user
    for pid in request.product_ids:
        if pid in ("1", "2") and settings.is_development:
            continue
        product = get_product_by_id(pid)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {pid} not found.")
        if product.get("user_id") and product.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail=f"Access denied to product {pid}.")

    extracted = _extract_facts_for_products(request.product_ids, user_id=user_id)

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

    # Compute summary metrics
    verified_count = sum(1 for c in checklist if c.get("marker") == "✓")
    caution_count = sum(1 for c in checklist if c.get("marker") == "⚠")
    missing_count = sum(1 for c in checklist if c.get("marker") == "?")
    conflict_count = sum(1 for c in checklist if c.get("marker") == "🚨")

    summary = {
        "total_items": len(checklist),
        "verified_items": verified_count,
        "caution_items": caution_count,
        "missing_items": missing_count,
        "conflict_items": conflict_count,
        "total_facts_reviewed": len(extracted["facts"]),
    }

    return {
        "checklist": checklist,
        "checklist_text": checklist_text_result.get("checklist"),
        "summary": summary,
    }


@router.post("/compare", response_model=LoanCompareResponse)
async def compare_products(
    request: LoanCompareRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Side-by-side comparative analysis of two or more loan products scoped to user.
    """
    user_id = current_user["id"]
    if len(request.product_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 product IDs are required for comparison.")

    # Validate ownership & fetch product metadata
    products_meta = []
    for pid in request.product_ids:
        if pid in ("1", "2") and settings.is_development:
            products_meta.append({"id": pid, "name": f"Sample Product {pid}", "issuer": "Sample Bank"})
            continue
        product = get_product_by_id(pid)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {pid} not found.")
        if product.get("user_id") and product.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail=f"Access denied to product {pid}.")
        products_meta.append(product)

    # Extract facts for each product individually to maintain strict product isolation
    product_facts_map = {}
    for p in products_meta:
        pid = str(p["id"])
        try:
            extracted = _extract_facts_for_products([pid], user_id=user_id)
            product_facts_map[pid] = extracted["facts"]
        except Exception:
            product_facts_map[pid] = []

    first_pid = str(products_meta[0]["id"])
    second_pid = str(products_meta[1]["id"])
    comparison_res = compare_loan_facts(
        product_a_facts=product_facts_map.get(first_pid, []),
        product_b_facts=product_facts_map.get(second_pid, []),
        scenario=request.scenario,
    )

    field_comparisons = comparison_res.get("field_comparison", [])

    # Generate natural-language comparison report
    comparison_report = generate_loan_comparison(
        products=products_meta,
        field_comparisons=field_comparisons,
        scenario=request.scenario,
    )

    return {
        "comparison_text": comparison_report.get("comparison"),
        "field_comparisons": field_comparisons,
        "products": products_meta,
        "summary": {
            "total_products": len(products_meta),
            "comparison_complete": comparison_res.get("comparison_complete", True),
            "comparison_summary": comparison_res.get("comparison_summary", ""),
        },
        "winner_summary": {
            "known_cost_a": comparison_res.get("known_cost_a"),
            "known_cost_b": comparison_res.get("known_cost_b"),
        },
    }



