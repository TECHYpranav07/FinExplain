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

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

from app.rag.retrieval.hybrid_retriever import hybrid_search
from app.rag.retrieval.reranker import rerank_chunks
from app.rag.context.builder import build_context
from app.rag.generation.generator import generate_answer
from app.rag.verification.grounder import ground_answer
from app.rag.enhancement.intent_classifier import classify_intent
from app.rag.enhancement.query_rewriter import rewrite_query
# FIN-021: generate_multi_queries import removed (result was discarded)
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
from app.guardrails.injection_guard import injection_guard
from app.guardrails.pii_guard import pii_guard
from app.guardrails.product_isolation import product_isolation_guard
from app.guardrails.answerability_guard import answerability_gate



def _is_fact_verified(fact, claim_results: Dict[str, Any]) -> bool:
    """FIN-006: Derive verified status from actual claim verification results.
    A fact is verified only if the claim verifier found a supporting claim
    that matches the fact's field or value."""
    claims = claim_results.get("claims", [])
    for c in claims:
        if not c.get("supported"):
            continue
        # Check if the verified claim relates to this fact
        claim_text = c.get("claim", "").lower()
        field_lower = fact.field.lower().replace("_", " ")
        if field_lower in claim_text:
            return True
        if fact.value and fact.value.lower() in claim_text:
            return True
    return False


def process_query(
    question: str,
    product_ids: List[str],
    max_retrieval: int = 30,
    max_context_tokens: int = 4000,
    user_id: Optional[str] = None,
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
    # Guardrail: Prompt Injection & PII Redaction
    # ===================================================================
    is_safe, injection_reason, clean_question = injection_guard.validate_query(question)
    if not is_safe:
        return {
            "answer": injection_reason,
            "confidence_score": 0.0,
            "confidence_label": "Security Block",
            "evidence_status": "NOT_SPECIFIED",
            "why_this_answer": "Query blocked: Suspicious prompt injection instruction detected.",
            "citations": [],
            "retrieved_chunks": [],
            "intent": "general",
            "evidence_score": 0,
            "missing_information": [],
            "conflicts": [],
            "key_facts": [],
            "status": "blocked",
        }

    clean_question, pii_count = pii_guard.redact_pii(clean_question)

    # ===================================================================
    # Step 1: Classify intent
    # ===================================================================
    intent_result = classify_intent(clean_question)
    logger.info(f"[Orchestrator] Intent: {intent_result.intent}, Confidence: {intent_result.confidence}")

    # ===================================================================
    # Step 2: Rewrite query
    # ===================================================================
    rewritten_query = rewrite_query(clean_question, intent_result.intent) or clean_question
    logger.info(f"[Orchestrator] Rewritten Query: {rewritten_query}")

    # ===================================================================
    # Step 3: Multi-query generation REMOVED (FIN-021)
    # The generated queries were logged then discarded — wasted LLM call.
    # ===================================================================

    # ===================================================================
    # Step 4: Hybrid retrieval
    # ===================================================================
    retrieved_chunks = hybrid_search(rewritten_query, product_ids, top_k=max_retrieval, user_id=user_id)
    if not retrieved_chunks and rewritten_query != question:
        retrieved_chunks = hybrid_search(question, product_ids, top_k=max_retrieval, user_id=user_id)

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
        logger.info(f"[Orchestrator] Chunk-level conflicts detected: {len(chunk_conflicts)}")

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
    logger.info("[Orchestrator] Extracting structured facts...")
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
    logger.info(f"[Orchestrator] Extracted {len(structured_facts)} structured facts")

    # ===================================================================
    # Step 9: Condition annotation (deterministic)
    # ===================================================================
    structured_facts = annotate_facts_with_conditions(structured_facts, reranked_chunks)

    # ===================================================================
    # Step 10: Missing information detection (deterministic)
    # ===================================================================
    missing_info = detect_missing_information(structured_facts)
    if missing_info:
        logger.info(f"[Orchestrator] Missing information: {[m['field'] for m in missing_info]}")

    # ===================================================================
    # Step 11: Fact-level conflict detection (deterministic)
    # ===================================================================
    fact_conflicts = detect_fact_conflicts(structured_facts)
    all_conflicts = chunk_conflicts + fact_conflicts
    if fact_conflicts:
        logger.info(f"[Orchestrator] Fact-level conflicts detected: {len(fact_conflicts)}")

    # ===================================================================
    # Step 12: Scenario extraction (if calculation intent)
    # ===================================================================
    scenario = {}
    if intent_result.intent in ("calculation", "comparison"):
        scenario = extract_user_scenario(question)
        if scenario:
            logger.info(f"[Orchestrator] Extracted scenario: {scenario}")

    # ===================================================================
    # Step 13: Calculation engine (deterministic)
    # ===================================================================
    calculation_result = None
    if scenario and scenario.get("principal"):
        # Extract rates from structured facts
        interest_rate = None
        processing_fee_rate = None
        processing_fee_type = "percent"  # FIN-028: distinguish fee types
        for fact in structured_facts:
            if fact.category == "interest_rate" and fact.value:
                try:
                    # FIN-028: skip values with qualifiers like "floating", "variable"
                    clean_val = fact.value.replace("%", "").strip()
                    if any(q in clean_val.lower() for q in ("floating", "variable", "linked", "reset")):
                        logger.info(f"[Orchestrator] Skipping qualified interest rate: {fact.value}")
                        continue
                    interest_rate = float(clean_val)
                except (ValueError, TypeError):
                    pass
            if fact.category == "processing_fee" and fact.value:
                try:
                    clean_val = fact.value.strip()
                    # FIN-028: detect if fee is fixed amount vs percentage
                    if any(c in clean_val for c in ("₹", "$", "Rs", "INR", "USD")):
                        # Fixed currency amount — strip currency symbols
                        numeric_val = clean_val.replace("₹", "").replace("$", "").replace("Rs", "").replace("INR", "").replace("USD", "").replace(",", "").strip()
                        processing_fee_rate = float(numeric_val)
                        processing_fee_type = "fixed"
                    else:
                        processing_fee_rate = float(clean_val.replace("%", "").strip())
                        processing_fee_type = "percent"
                except (ValueError, TypeError):
                    pass

        # FIN-028: Convert tenure to months using repayment_unit
        tenure_months = scenario.get("repayment_period")
        repayment_unit = scenario.get("repayment_unit", "months").lower()
        if tenure_months is not None:
            if repayment_unit in ("year", "years", "yr", "yrs"):
                tenure_months = int(tenure_months) * 12
                logger.info(f"[Orchestrator] Converted {scenario.get('repayment_period')} {repayment_unit} → {tenure_months} months")
            else:
                tenure_months = int(tenure_months)

        calculation_result = calculate_loan_scenario(
            principal=scenario.get("principal"),
            interest_rate=interest_rate,
            tenure=tenure_months,
            processing_fee=processing_fee_rate,
            processing_fee_type=processing_fee_type,
            evidence_ids=[f.source_chunk_id for f in structured_facts if f.source_chunk_id],
        )
    # ===================================================================
    # Step 14: Cost driver & Risk factor detection (deterministic)
    # ===================================================================
    is_product_audit_query = (
        intent_result.intent in ("review", "summary", "comparison", "risk")
        or any(k in clean_question.lower() for k in ("confidence score", "risk score", "risk factor", "how risky", "audit report", "detailed report", "quality score", "risk report", "summarize", "summary"))
    )
    if is_product_audit_query:
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
    else:
        risk_factors = []
        risk_score_result = {"score": None, "level": None}

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
    logger.info("[Orchestrator] Verifying claims...")
    claim_results = verify_all_claims(answer_text, structured_facts, reranked_chunks)
    logger.info(
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
    logger.info(f"[Orchestrator] Evidence score: {evidence_score_result['score']}/100 ({evidence_score_result['label']})")

    # ===================================================================
    # Step 18: Response validation (deterministic)
    # ===================================================================
    validation = validate_final_response(
        answer_text,
        claim_results,
        structured_facts,
        reranked_chunks,
        calculation_result,
        is_meta_query=is_product_audit_query,
    )
    if not validation["valid"]:
        logger.info(f"[Orchestrator] Validation issues: {validation['issues']}")
        answer_text = validation["sanitized_answer"]

    # Guardrail: Anti-Averaging and Product Isolation Check
    is_isolated, answer_text = product_isolation_guard.verify_no_rate_averaging(
        answer_text,
        is_explicit_average_query=("average" in clean_question.lower() or "mean" in clean_question.lower())
    )

    # ===================================================================
    # Step 19: Determine overall evidence status
    # ===================================================================
    statuses = set(f.status for f in structured_facts)
    if all_conflicts or EvidenceStatus.CONFLICTED in statuses or EvidenceStatus.MIXED in statuses:
        overall_status = "CONFLICTED"
    elif EvidenceStatus.PARTIAL in statuses:
        overall_status = "PARTIAL"
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

    # Construct transparent why_this_answer explanation
    if overall_status == "NOT_SPECIFIED" and intent_result.intent == "recommendation":
        why_this_answer = (
            "You asked for subjective recommendation advice (e.g. why to choose or avoid this loan) with exact citations. "
            "Because loan agreements only contain legal terms, fees, and interest benchmarks—not promotional advice—"
            "synthesized claims could not be verified against the source text. "
            "To prevent AI hallucinations, FinExplain blocked ungrounded statements and generated actionable lender questions instead."
        )
    elif not validation["valid"] and claim_results.get("unsupported_claims", 0) > 0:
        why_this_answer = (
            "Certain claims could not be verified with complete evidence from the document. "
            "FinExplain flagged unverified aspects to maintain accuracy."
        )
    elif overall_status in ("CONFLICTED", "MIXED"):
        why_this_answer = (
            "Conflicting terms were identified across document sections or schedules. "
            "FinExplain highlighted the discrepancies to prevent misleading calculations."
        )
    elif overall_status == "PARTIAL":
        why_this_answer = (
            "The retrieved evidence supports part of your inquiry. "
            "FinExplain provided the verified facts and flagged unverified terms."
        )
    elif overall_status == "CONDITIONAL":
        why_this_answer = (
            "Terms are subject to specific preconditions (e.g. conditional fees or penalty terms). "
            "FinExplain validated that clauses only apply under specific circumstances."
        )
    else:
        why_this_answer = (
            "All factual claims were verified with high-confidence exact matches against the retrieved loan document text."
        )

    # ===================================================================
    # Step 20: Evaluate Human-In-The-Loop (HITL) Trigger Policy
    # ===================================================================
    hitl_required = False
    hitl_reason = None
    hitl_type = "GENERAL"

    # Check if user query directly targets a missing field
    q_lower = clean_question.lower()
    targeted_missing = [
        m for m in missing_info 
        if m.get("field") in ("apr", "interest_rate", "repayment_schedule") 
        and (m.get("field", "").replace("_", " ") in q_lower or (m.get("field") == "apr" and "apr" in q_lower))
    ]

    if overall_status in ("CONFLICTED", "MIXED") or (all_conflicts and len(all_conflicts) > 0 and ("conflict" in q_lower or intent_result.intent in ("comparison", "review"))):
        hitl_required = True
        hitl_type = "CONFLICT_REVIEW"
        hitl_reason = (
            f"Discrepancy detected across document sources ({len(all_conflicts)} conflict(s) identified). "
            "Borrower or loan officer verification required before executing agreement."
        )
    elif (risk_score_result.get("score") or 0) >= 70 and intent_result.intent in ("review", "summary", "comparison"):
        hitl_required = True
        hitl_type = "RISK_ACCEPTANCE"
        hitl_reason = (
            f"Document-derived Risk Rating is {risk_score_result.get('score') or 0}/100 ({risk_score_result.get('level') or 'HIGH'}). "
            "Predatory penalty terms or significant cost disclosure gaps require explicit acknowledgment."
        )
    elif targeted_missing:
        hitl_required = True
        hitl_type = "DISCLOSURE_GAP"
        hitl_reason = (
            f"The requested parameter ('{targeted_missing[0].get('field', '').replace('_', ' ').upper()}') is missing from the uploaded documents."
        )

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

        # --- HITL Escalation Fields ---
        "hitl_required": hitl_required,
        "hitl_reason": hitl_reason,
        "hitl_type": hitl_type,
        "hitl_status": "PENDING" if hitl_required else None,

        # --- New structured fields ---
        "why_this_answer": why_this_answer,
        "key_facts": facts_dicts,
        "conditions": [
            f.model_dump() for f in structured_facts
            if f.status == EvidenceStatus.CONDITIONAL
        ],
        "calculations": [calculation_result] if calculation_result else [],
        # FIN-006: Derive verified status from actual claim verification
        # instead of hardcoding True for every fact with a source chunk.
        "evidence": [
            {
                "claim": f.field,
                "document": f.source_document,
                "page": f.page,
                "section": f.section,
                "chunk_id": f.source_chunk_id,
                "status": f.status.value,
                "verified": _is_fact_verified(f, claim_results),
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
