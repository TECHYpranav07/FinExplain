"""
FinExplain RAG Orchestrator — Evidence-First Pipeline.

Pipeline stages:
  0.  Cache check
  1.  Intent classification
  2.  Query rewriting
  3.  Multi-query generation
  4.  Hybrid retrieval  (Dense + BM25 via RRF)
  5.  Chunk-level conflict detection
  6.  Cross-encoder reranking
  7.  Context building

  --- NEW STAGES ---
  8.  Structured fact extraction
  9.  Condition annotation (deterministic)
  10. Missing information detection (deterministic)
  11. Fact-level conflict detection (deterministic)
  12. Scenario extraction (LLM)
  13. Calculation engine (deterministic)
  14. Cost driver detection (deterministic)

  15. LLM answer generation (with structured context)
  16. Claim-level verification (LLM + deterministic)
  17. Evidence scoring (deterministic)
  18. Response validation (deterministic)
  19. HILT escalation (if needed)
  20. Cache storage
"""

from typing import List, Dict, Any

from app.rag.retrieval.hybrid_retriever import hybrid_search
from app.rag.retrieval.reranker import rerank_chunks
from app.rag.context.builder import build_context
from app.rag.generation.generator import generate_answer
from app.rag.verification.grounder import ground_answer
from app.rag.enhancement.intent_classifier import classify_intent
from app.rag.enhancement.query_rewriter import rewrite_query
from app.rag.enhancement.multi_query import generate_multi_queries
from app.rag.verification.conflict_detector import detect_conflicts, detect_fact_conflicts
from app.rag.verification.confidence import calculate_confidence, evidence_scorer
from app.rag.verification.claim_verifier import verify_all_claims
from app.rag.verification.response_validator import validate_final_response
from app.rag.extraction.fact_extractor import extract_structured_facts
from app.rag.extraction.condition_detector import annotate_facts_with_conditions
from app.rag.extraction.missing_detector import detect_missing_information
from app.rag.extraction.scenario_extractor import extract_user_scenario
from app.rag.extraction.cost_driver_detector import detect_cost_drivers
from app.rag.extraction.risk_engine import risk_engine
from app.rag.extraction.lender_questions import generate_lender_questions
from app.core.loan_categories import EvidenceStatus
from app.tools.calculator import calculate_loan_scenario
from app.cache.query_cache import get_cached_response, set_cached_response


def process_query(
    question: str,
    product_ids: List[str],
    max_retrieval: int = 30,
    max_context_tokens: int = 4000,
) -> Dict[str, Any]:
    """
    Enhanced evidence-first RAG pipeline.

    Retrieve → Extract → Calculate → Explain → Verify → Score → Present
    """

    # ===================================================================
    # Step 0: Check cache
    # ===================================================================
    cached = get_cached_response(question, product_ids)
    if cached:
        return cached

    # ===================================================================
    # Step 1: Classify intent
    # ===================================================================
    intent_result = classify_intent(question)
    print(f"[Orchestrator] Intent: {intent_result.intent}, Confidence: {intent_result.confidence}")

    # ===================================================================
    # Step 2: Rewrite query
    # ===================================================================
    rewritten_query = rewrite_query(question, intent_result.intent) or question
    print(f"[Orchestrator] Rewritten Query: {rewritten_query}")

    # ===================================================================
    # Step 3: Generate multi-queries
    # ===================================================================
    queries = generate_multi_queries(rewritten_query, num_queries=3)
    print(f"[Orchestrator] Multi-queries: {queries}")

    # ===================================================================
    # Step 4: Hybrid retrieval
    # ===================================================================
    retrieved_chunks = hybrid_search(rewritten_query, product_ids, top_k=max_retrieval)
    if not retrieved_chunks and rewritten_query != question:
        retrieved_chunks = hybrid_search(question, product_ids, top_k=max_retrieval)

    if not retrieved_chunks:
        return {
            "answer": "No relevant information found.",
            "confidence_score": 0.0,
            "confidence_label": "No Evidence",
            "citations": [],
            "intent": intent_result.intent,
            "evidence_score": 0,
            "missing_information": [],
            "conflicts": [],
            "key_facts": [],
        }

    # ===================================================================
    # Step 5: Chunk-level conflict detection (original)
    # ===================================================================
    chunk_conflicts = detect_conflicts(retrieved_chunks)
    if chunk_conflicts:
        print(f"[Orchestrator] Chunk-level conflicts detected: {len(chunk_conflicts)}")

    # ===================================================================
    # Step 6: Rerank
    # ===================================================================
    reranked_chunks = rerank_chunks(rewritten_query, retrieved_chunks, top_k=10)
    rerank_scores = [c.get("rerank_score", 0.5) for c in reranked_chunks]

    # ===================================================================
    # Step 7: Build context
    # ===================================================================
    context = build_context(reranked_chunks, max_tokens=max_context_tokens)

    if not context:
        return {
            "answer": "Unable to build context.",
            "confidence_score": 0.0,
            "confidence_label": "No Evidence",
            "citations": [],
            "retrieved_chunks": reranked_chunks,
            "intent": intent_result.intent,
            "evidence_score": 0,
            "missing_information": [],
            "conflicts": [],
            "key_facts": [],
        }

    # ===================================================================
    # Step 8: Structured fact extraction
    # ===================================================================
    print("[Orchestrator] Extracting structured facts...")
    product_name = None
    document_name = None
    if reranked_chunks:
        metadata = reranked_chunks[0].get("metadata") or {}
        product_name = reranked_chunks[0].get("product_name") or metadata.get("product_name")
        document_name = reranked_chunks[0].get("document_name") or metadata.get("document_name")

    structured_facts = extract_structured_facts(
        reranked_chunks,
        product_name=product_name,
        document_name=document_name,
    )
    print(f"[Orchestrator] Extracted {len(structured_facts)} structured facts")

    # ===================================================================
    # Step 9: Condition annotation (deterministic)
    # ===================================================================
    structured_facts = annotate_facts_with_conditions(structured_facts, reranked_chunks)

    # ===================================================================
    # Step 10: Missing information detection (deterministic)
    # ===================================================================
    missing_info = detect_missing_information(structured_facts)
    if missing_info:
        print(f"[Orchestrator] Missing information: {[m['field'] for m in missing_info]}")

    # ===================================================================
    # Step 11: Fact-level conflict detection (deterministic)
    # ===================================================================
    fact_conflicts = detect_fact_conflicts(structured_facts)
    all_conflicts = chunk_conflicts + fact_conflicts
    if fact_conflicts:
        print(f"[Orchestrator] Fact-level conflicts detected: {len(fact_conflicts)}")

    # ===================================================================
    # Step 12: Scenario extraction (if calculation intent)
    # ===================================================================
    scenario = {}
    if intent_result.intent in ("calculation", "comparison"):
        scenario = extract_user_scenario(question)
        if scenario:
            print(f"[Orchestrator] Extracted scenario: {scenario}")

    # ===================================================================
    # Step 13: Calculation engine (deterministic)
    # ===================================================================
    calculation_result = None
    if scenario and scenario.get("principal"):
        # Extract rates from structured facts
        interest_rate = None
        processing_fee_rate = None
        for fact in structured_facts:
            if fact.category == "interest_rate" and fact.value:
                try:
                    interest_rate = float(fact.value.replace("%", "").strip())
                except (ValueError, TypeError):
                    pass
            if fact.category == "processing_fee" and fact.value:
                try:
                    processing_fee_rate = float(fact.value.replace("%", "").strip())
                except (ValueError, TypeError):
                    pass

        calculation_result = calculate_loan_scenario(
            principal=scenario.get("principal"),
            interest_rate=interest_rate,
            tenure=scenario.get("repayment_period"),
            processing_fee=processing_fee_rate,
            evidence_ids=[f.source_chunk_id for f in structured_facts if f.source_chunk_id],
        )
        print(f"[Orchestrator] Calculation complete. Unknown costs: {calculation_result.get('unknown_costs', [])}")

    # ===================================================================
    # Step 14: Cost driver & Risk factor detection (deterministic)
    # ===================================================================
    cost_drivers = detect_cost_drivers(structured_facts)
    risk_factors = risk_engine.detect_risk_factors(
        facts=structured_facts,
        missing=missing_info,
        conflicts=all_conflicts,
        scenario=scenario,
    )
    risk_score_result = risk_engine.calculate_risk_score(risk_factors)
    lender_questions = generate_lender_questions(
        facts=structured_facts,
        missing=missing_info,
        conflicts=all_conflicts,
        risk_factors=risk_factors,
        scenario=scenario,
    )

    # ===================================================================
    # Step 15: Generate answer (with structured context)
    # ===================================================================
    facts_dicts = [f.model_dump() for f in structured_facts]
    generation_result = generate_answer(
        question,
        context,
        structured_facts=facts_dicts,
        calculation_results=calculation_result,
        conflicts=all_conflicts,
        missing_information=missing_info,
        scenario=scenario,
    )

    if "error" in generation_result:
        return {
            "answer": generation_result["answer"],
            "confidence_score": 0.0,
            "confidence_label": "Error",
            "citations": [],
            "retrieved_chunks": reranked_chunks,
            "intent": intent_result.intent,
            "evidence_score": 0,
            "missing_information": missing_info,
            "conflicts": all_conflicts,
            "key_facts": facts_dicts,
        }

    answer_text = generation_result["answer"]

    # ===================================================================
    # Step 16: Claim-level verification
    # ===================================================================
    print("[Orchestrator] Verifying claims...")
    claim_results = verify_all_claims(answer_text, structured_facts, reranked_chunks)
    print(
        f"[Orchestrator] Claims: {claim_results['total_claims']}, "
        f"Supported: {claim_results['supported_claims']}, "
        f"Unsupported: {claim_results['unsupported_claims']}"
    )

    # ===================================================================
    # Step 17: Evidence scoring (deterministic)
    # ===================================================================
    evidence_score_result = evidence_scorer.calculate_evidence_score(
        claim_results=claim_results,
        facts=structured_facts,
        conflicts=all_conflicts,
        missing=missing_info,
        calculation_result=calculation_result,
        rerank_scores=rerank_scores,
    )
    print(f"[Orchestrator] Evidence score: {evidence_score_result['score']}/100 ({evidence_score_result['label']})")

    # ===================================================================
    # Step 18: Response validation (deterministic)
    # ===================================================================
    validation = validate_final_response(
        answer_text,
        claim_results,
        structured_facts,
        reranked_chunks,
        calculation_result,
    )
    if not validation["valid"]:
        print(f"[Orchestrator] Validation issues: {validation['issues']}")
        answer_text = validation["sanitized_answer"]

    # ===================================================================
    # Step 19: Determine overall evidence status
    # ===================================================================
    statuses = set(f.status for f in structured_facts)
    if EvidenceStatus.MIXED in statuses:
        overall_status = "MIXED"
    elif EvidenceStatus.CONDITIONAL in statuses and EvidenceStatus.EXPLICIT in statuses:
        overall_status = "CONDITIONAL"
    elif EvidenceStatus.EXPLICIT in statuses:
        overall_status = "EXPLICIT"
    elif EvidenceStatus.CONDITIONAL in statuses:
        overall_status = "CONDITIONAL"
    else:
        overall_status = "NOT_SPECIFIED"

    # ===================================================================
    # Build the final response (backward-compatible + structured)
    # ===================================================================
    # Also run the old grounder for backward-compatible citation data
    grounded = ground_answer(answer_text, reranked_chunks, rerank_scores)

    result: Dict[str, Any] = {
        # --- Backward-compatible fields ---
        "answer": answer_text,
        "confidence_score": evidence_score_result["score_normalized"],
        "confidence_label": evidence_score_result["label"],
        "citations": grounded.get("citations", []),
        "retrieved_chunks": reranked_chunks,
        "context_used": context,
        "intent": intent_result.intent,
        "status": "ok",

        # --- New structured fields ---
        "key_facts": facts_dicts,
        "conditions": [
            f.model_dump() for f in structured_facts
            if f.status == EvidenceStatus.CONDITIONAL
        ],
        "calculations": [calculation_result] if calculation_result else [],
        "evidence": [
            {
                "claim": f.field,
                "document": f.source_document,
                "page": f.page,
                "section": f.section,
                "chunk_id": f.source_chunk_id,
                "status": f.status.value,
                "verified": True,
            }
            for f in structured_facts
            if f.source_chunk_id
        ],
        "missing_information": missing_info,
        "conflicts": all_conflicts,
        "evidence_status": overall_status,
        "what_to_verify": [
            m["field"].replace("_", " ").title() for m in missing_info
        ],
        "evidence_score": evidence_score_result["score"],
        "evidence_score_details": evidence_score_result,
        "claim_coverage": claim_results.get("claim_coverage", 0.0),
        "claim_verification": claim_results,
        "calculation_valid": (
            calculation_result is not None
            and len(calculation_result.get("unknown_costs", [])) == 0
        ) if calculation_result else True,
        "cost_drivers": cost_drivers,
        "risk_factors": risk_factors,
        "risk_score": risk_score_result["score"],
        "risk_level": risk_score_result["level"],
        "risk_details": risk_score_result,
        "questions_to_ask_provider": lender_questions,
        "scenario": scenario,
        "validation": validation,
    }

    # ===================================================================
    # Step 20: HILT escalation (if evidence score is very low)
    # ===================================================================
    if evidence_score_result["score"] < 40:
        from app.hilt.workflow import escalate_to_hilt
        hilt_result = escalate_to_hilt(question, product_ids)
        result["status"] = "hilt_escalated"
        result["hilt_info"] = hilt_result

    # ===================================================================
    # Step 21: Cache
    # ===================================================================
    set_cached_response(question, product_ids, result)

    return result
