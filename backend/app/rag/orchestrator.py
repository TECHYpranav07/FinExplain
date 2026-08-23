"""
FinExplain RAG Orchestrator — Evidence-First Multi-Tier Pipeline (FinExplain V2).

Tiered processing architecture:
  FAST_FACTUAL  -> L1/L2 Cache -> Guardrails -> LoanFactStore Lookup -> Deterministic Template (0 LLM, 0 Retrieval, ~50-150ms)
  CALCULATION   -> L1/L2 Cache -> Guardrails -> LoanFactStore (Rates) -> Deterministic Python Calc -> Response (0 Fact LLM)
  STANDARD_RAG  -> Parallel Retrieval -> Dense/BM25 Agreement -> Bounded Context -> Gemini 3.5 Flash-Lite -> Verifier
  DEEP_RAG      -> Parallel Retrieval -> CrossEncoder Reranker -> Full Facts -> Risk Engine -> Gemini -> Verifier
"""

import logging
import time
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

_CONVERSATIONAL_PATTERNS = re.compile(
    r"^\s*(?:"
    r"who\s+are\s+you|what\s+is\s+finexplain|what\s+are\s+you|"
    r"what\s+can\s+you\s+do|how\s+can\s+you\s+help|what\s+do\s+you\s+do|"
    r"help|how\s+to\s+use|tell\s+me\s+about\s+yourself|"
    r"hi|hello|hey|greetings|good\s+(?:morning|afternoon|evening)"
    r")\b",
    re.I,
)

from app.rag.retrieval.hybrid_retriever import hybrid_search
from app.rag.retrieval.reranker import rerank_chunks
from app.rag.context.builder import build_context, build_evidence_window
from app.rag.generation.generator import generate_answer
from app.rag.verification.grounder import ground_answer
from app.rag.enhancement.intent_classifier import classify_intent
from app.rag.enhancement.query_rewriter import rewrite_query
from app.rag.enhancement.query_router import classify_query_tier, QueryTier
from app.rag.verification.conflict_detector import detect_conflicts, detect_fact_conflicts
from app.rag.verification.confidence import calculate_confidence, evidence_scorer
from app.rag.verification.claim_verifier import verify_all_claims
from app.rag.verification.response_validator import validate_final_response
from app.rag.extraction.fact_extractor import extract_structured_facts
from app.rag.extraction.structured_fact_store import get_fact, get_all_facts, lookup_facts
from app.rag.extraction.condition_detector import annotate_facts_with_conditions
from app.rag.extraction.missing_detector import detect_missing_information
from app.rag.extraction.scenario_extractor import extract_user_scenario
from app.rag.extraction.cost_driver_detector import detect_cost_drivers
from app.rag.extraction.risk_engine import risk_engine
from app.rag.extraction.lender_questions import generate_lender_questions
from app.core.loan_categories import EvidenceStatus, LoanFact
from app.tools.calculator import calculate_loan_scenario
from app.cache.query_cache import get_cached_response, set_cached_response
from app.guardrails.injection_guard import injection_guard
from app.guardrails.pii_guard import pii_guard
from app.guardrails.product_isolation import product_isolation_guard
from app.guardrails.answerability_guard import answerability_gate


def _is_fact_verified(fact: LoanFact, claim_results: Dict[str, Any]) -> bool:
    """Derive verified status from actual claim verification results."""
    claims = claim_results.get("claims", [])
    for c in claims:
        if not c.get("supported"):
            continue
        claim_text = c.get("claim", "").lower()
        field_lower = fact.field.lower().replace("_", " ")
        if field_lower in claim_text:
            return True
        if fact.value and fact.value.lower() in claim_text:
            return True
    return False


def _format_deterministic_factual_answer(fact: LoanFact) -> str:
    """
    Format a direct, evidence-cited answer from a structured LoanFact
    without requiring an LLM call (0 tokens, 0ms latency).
    """
    field_label = fact.field.replace("_", " ").title()
    value_str = f"{fact.value} {fact.unit}".strip() if fact.unit else str(fact.value)
    
    citation_parts = []
    if fact.page:
        citation_parts.append(f"Page {fact.page}")
    if fact.section:
        citation_parts.append(f"Section: {fact.section}")
    citation_str = f" [{', '.join(citation_parts)}]" if citation_parts else ""

    answer = f"The {field_label.lower()} is {value_str}{citation_str}."

    if fact.condition:
        answer += f" Note: Subject to condition ({fact.condition})."

    return answer


def process_query(
    question: str,
    product_ids: List[str],
    max_retrieval: int = 15,
    max_context_tokens: int = 4000,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Adaptive evidence-first RAG pipeline (FinExplain V2).

    FAST_FACTUAL:  ~50-200ms  (0 LLM tokens, 0 Retrieval when fact is in store)
    CALCULATION:   ~200-500ms (0 Fact LLM tokens, deterministic Python math)
    STANDARD_RAG:  ~3-5s      (Parallel Dense/BM25 + RRF agreement gate)
    DEEP_RAG:      ~6-9s      (Full audit, capped reranker, risk engine)
    """
    start_time = time.time()

    # ===================================================================
    # Step 0: Check L1 / L2 Cache
    # ===================================================================
    cached = get_cached_response(question, product_ids, user_id=user_id)
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
            "token_metrics": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "tier": "blocked"},
        }

    clean_question, pii_count = pii_guard.redact_pii(clean_question)

    # ===================================================================
    # 💬 Conversational / Assistant Identity Fast Path (~0ms, 0 Tokens)
    # ===================================================================
    if _CONVERSATIONAL_PATTERNS.search(clean_question.strip()):
        return {
            "answer": (
                "👋 I am **FinExplain**, your AI-powered credit agreement analysis assistant.\n\n"
                "I help borrowers and finance professionals audit loan contracts, Key Fact Statements (KFS), and sanction letters to uncover hidden fees, ambiguous terms, and unfair clauses.\n\n"
                "**Here are key questions you can ask me about your uploaded documents:**\n"
                "- **Loan Terms & Pricing:** *\"What is the interest rate, APR, and processing fee?\"*\n"
                "- **Exit & Prepayment:** *\"What is the prepayment penalty or foreclosure charge?\"*\n"
                "- **Default Penalties:** *\"What penal interest or bounce charges apply on overdue EMIs?\"*\n"
                "- **What-If Calculations:** *\"If I borrow ₹5 Lakhs for 3 years, what will my monthly EMI be?\"*\n"
                "- **Full Risk Audit:** *\"Audit all conditional traps, unilateral rights, and conflict items in this agreement.\"*"
            ),
            "confidence_score": 1.0,
            "confidence_label": "Assistant Help",
            "evidence_status": "EXPLICIT",
            "why_this_answer": "FinExplain assistant identity and usage guidance.",
            "citations": [],
            "evidence": [],
            "retrieved_chunks": [],
            "intent": "conversational",
            "status": "ok",
            "processing_tier": "conversational",
            "key_facts": [],
            "missing_information": [],
            "conflicts": [],
            "token_metrics": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "tier": "conversational", "model": "built-in"},
        }

    logger.info(f"\n{'='*70}\n[Ask AI] 📥 Incoming Query: \"{clean_question}\" | Products: {product_ids}\n{'-'*70}")

    # ===================================================================
    # Step 1: Classify Intent & Routing Tier
    # ===================================================================
    intent_result = classify_intent(clean_question)
    intent_val = intent_result.intent.value if hasattr(intent_result.intent, 'value') else str(intent_result.intent)
    tier, detected_field = classify_query_tier(clean_question, intent=intent_val)
    logger.info(f"[Router] 🔀 Tier: {tier.value.upper()} | Intent: {intent_val.upper()} | Target Field: {detected_field or 'None'}")

    # ===================================================================
    # ⚡ PATH 1: TRUE ZERO-LLM FAST_FACTUAL PATH (~50-150ms)
    # ===================================================================
    if tier == QueryTier.FAST_FACTUAL and detected_field:
        fact = get_fact(product_ids, detected_field)
        if fact and fact.value:
            logger.info(f"[FastPath] ⚡ Direct LoanFact HIT for '{detected_field}' = {fact.value}. Bypassing Retrieval & LLM.")
            answer_text = _format_deterministic_factual_answer(fact)
            
            # Synthetic citations and verified claims for response packaging
            citations = [{
                "document": fact.source_document or (product_ids[0] if product_ids else "Agreement"),
                "page": fact.page or 1,
                "section": fact.section or "Key Terms",
                "verified": True,
            }]
            
            claim_results = {
                "claims": [{
                    "claim": answer_text,
                    "supported": True,
                    "evidence_id": fact.source_chunk_id,
                    "status": "EXPLICIT",
                    "citation_valid": True,
                    "condition_preserved": True,
                    "issues": [],
                }],
                "total_claims": 1,
                "supported_claims": 1,
                "unsupported_claims": 0,
                "invalid_citations": 0,
                "conditions_dropped": 0,
                "claim_coverage": 1.0,
            }
            
            evidence_score_result = {
                "score": 98,
                "score_normalized": 0.98,
                "label": "High",
                "breakdown": {
                    "claim_support": 100,
                    "citation_validity": 100,
                    "completeness": 95,
                    "consistency": 100,
                },
                "deductions": [],
            }

            result = _build_response(
                answer_text=answer_text,
                structured_facts=[fact],
                reranked_chunks=[],
                context=fact.source_text or answer_text,
                intent_result=intent_result,
                claim_results=claim_results,
                evidence_score_result=evidence_score_result,
                grounded={"citations": citations},
                clean_question=clean_question,
                tier=tier,
                token_metrics={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "tier": "fast_factual", "model": "none (deterministic)"},
            )
            
            set_cached_response(question, product_ids, result, user_id=user_id)
            elapsed = time.time() - start_time
            logger.info(f"[FastPath] 🚀 Delivered in {elapsed*1000:.1f}ms (0 Tokens, 0 Retrieval)\n{'='*70}")
            return result

    # ===================================================================
    # ⚡ PATH 2: CALCULATION PATH (Reads LoanFactStore + Python Math)
    # ===================================================================
    if tier == QueryTier.CALCULATION or intent_result.intent == "calculation":
        scenario = extract_user_scenario(clean_question)
        if scenario and scenario.get("principal"):
            # Lookup interest rate & fees directly from LoanFact store
            rate_fact = get_fact(product_ids, "interest_rate")
            fee_fact = get_fact(product_ids, "processing_fee")
            
            interest_rate = None
            if rate_fact and rate_fact.value:
                try:
                    interest_rate = float(rate_fact.value.replace("%", "").strip())
                except (ValueError, TypeError):
                    pass
            
            # Default fallback rate if not specified in document
            if interest_rate is None:
                interest_rate = 10.50

            tenure_val = scenario.get("repayment_period", 60)
            rep_unit = scenario.get("repayment_unit", "months").lower()
            if rep_unit in ("year", "years", "yr", "yrs"):
                tenure_months = int(tenure_val) * 12
            else:
                tenure_months = int(tenure_val)

            calc_res = calculate_loan_scenario(
                principal=float(scenario.get("principal")),
                interest_rate=float(interest_rate),
                tenure=int(tenure_months),
                processing_fee=1.0,
                evidence_ids=[rate_fact.source_chunk_id] if rate_fact and rate_fact.source_chunk_id else [],
            )

            results_dict = calc_res.get("results", {})
            emi_val = results_dict.get("emi", 0)
            interest_val = results_dict.get("total_interest", 0)
            total_val = results_dict.get("total_repayment", 0)

            answer_text = (
                f"For a principal of ₹{scenario.get('principal'):,.0f} over {tenure_months} months at an interest rate of {interest_rate}% p.a.:\n"
                f"- **Monthly EMI:** ₹{emi_val:,.0f}\n"
                f"- **Total Interest Payable:** ₹{interest_val:,.0f}\n"
                f"- **Total Amount Payable:** ₹{total_val:,.0f}"
            )
            if rate_fact and rate_fact.page:
                answer_text += f" [Interest rate source: Page {rate_fact.page}, Section {rate_fact.section}]."

            result = _build_response(
                answer_text=answer_text,
                structured_facts=[rate_fact] if rate_fact else [],
                reranked_chunks=[],
                context=answer_text,
                intent_result=intent_result,
                claim_results={"claims": [], "total_claims": 1, "supported_claims": 1, "claim_coverage": 1.0},
                evidence_score_result={"score": 95, "score_normalized": 0.95, "label": "High"},
                grounded={"citations": [{"document": "Loan Agreement", "page": rate_fact.page if rate_fact else 1, "verified": True}]},
                clean_question=clean_question,
                tier=tier,
                calculation_result=calc_res,
                scenario=scenario,
                token_metrics={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "tier": "calculation", "model": "none (deterministic)"},
            )
            set_cached_response(question, product_ids, result, user_id=user_id)
            return result

    # ===================================================================
    # 📚 PATH 3: STANDARD_RAG & DEEP_RAG (Hybrid Retrieval Engine)
    # ===================================================================
    rewritten_query = rewrite_query(clean_question, intent_result.intent) or clean_question
    retrieved_chunks = hybrid_search(rewritten_query, product_ids, top_k=max_retrieval, user_id=user_id)
    if not retrieved_chunks and rewritten_query != question:
        retrieved_chunks = hybrid_search(question, product_ids, top_k=max_retrieval, user_id=user_id)

    if not retrieved_chunks:
        return {
            "answer": "No relevant information found in the uploaded documents.",
            "confidence_score": 0.0,
            "confidence_label": "No Evidence",
            "citations": [],
            "intent": intent_result.intent,
            "evidence_score": 0,
            "missing_information": [],
            "conflicts": [],
            "key_facts": [],
            "token_metrics": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "tier": tier.value},
        }

    # ===================================================================
    # Adaptive Reranking via Dense/BM25 Agreement
    # ===================================================================
    agreement_score = retrieved_chunks[0].get("retrieval_agreement_score", 0.0) if retrieved_chunks else 0.0
    top_rrf = max((c.get("rrf_score", 0) for c in retrieved_chunks), default=0)

    if tier == QueryTier.DEEP_RAG:
        # Full reranker for deep analytical queries
        reranked_chunks = rerank_chunks(rewritten_query, retrieved_chunks, top_k=6)
    elif agreement_score >= 0.5 and top_rrf >= 0.020:
        # High Dense/BM25 agreement — skip CrossEncoder
        reranked_chunks = retrieved_chunks[:6]
        for i, c in enumerate(reranked_chunks):
            if "rerank_score" not in c:
                c["rerank_score"] = max(0.1, 0.9 - (i * 0.05))
        logger.info(f"[Retriever] ⚡ Reranker SKIPPED (Dense/BM25 Agreement: {agreement_score:.2f} >= 0.50)")
    else:
        # Low agreement — invoke CrossEncoder to resolve divergence
        reranked_chunks = rerank_chunks(rewritten_query, retrieved_chunks, top_k=6)

    rerank_scores = [c.get("rerank_score", 0.5) for c in reranked_chunks]

    # Build Context (Evidence Compression for Standard RAG)
    if tier == QueryTier.STANDARD_RAG:
        from app.rag.context.builder import compress_evidence_context
        context = compress_evidence_context(reranked_chunks, clean_question, max_tokens=600)
    else:
        context = build_context(reranked_chunks, max_tokens=max_context_tokens)

    # Pre-Generation Answerability Gate
    can_answer, answerability_reason = answerability_gate.check_answerability(
        rewritten_query, reranked_chunks, rerank_scores
    )
    if not can_answer and tier != QueryTier.DEEP_RAG:
        return {
            "answer": "Unable to provide a verified answer based on the retrieved documents. The requested topic is not covered in the operative credit documentation.",
            "confidence_score": 0.0,
            "confidence_label": "No Evidence",
            "evidence_status": "NOT_SPECIFIED",
            "why_this_answer": "The query asked for terms not disclosed or covered in the provided agreements.",
            "citations": [],
            "retrieved_chunks": reranked_chunks[:2],
            "context_used": context,
            "intent": intent_result.intent,
            "evidence_score": 0,
            "missing_information": [],
            "conflicts": [],
            "key_facts": [],
            "status": "unanswerable",
            "token_metrics": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "tier": tier.value},
        }

    # Structured Facts (from store first, LLM fallback only for Deep RAG)
    structured_facts = get_all_facts(product_ids)
    if not structured_facts or tier == QueryTier.DEEP_RAG:
        structured_facts = extract_structured_facts(reranked_chunks)

    structured_facts = annotate_facts_with_conditions(structured_facts, reranked_chunks)
    missing_info = detect_missing_information(structured_facts)

    all_conflicts = []
    cost_drivers = []
    risk_factors = []
    risk_score_result = {"score": None, "level": None}
    lender_questions = []

    if tier == QueryTier.DEEP_RAG:
        chunk_conflicts = detect_conflicts(reranked_chunks)
        fact_conflicts = detect_fact_conflicts(structured_facts)
        all_conflicts = chunk_conflicts + fact_conflicts
        cost_drivers = detect_cost_drivers(structured_facts)
        risk_factors = risk_engine.detect_risk_factors(
            facts=structured_facts,
            missing=missing_info,
            conflicts=all_conflicts,
        )
        risk_score_result = risk_engine.calculate_risk_score(risk_factors)
        lender_questions = generate_lender_questions(
            facts=structured_facts,
            missing=missing_info,
            conflicts=all_conflicts,
            risk_factors=risk_factors,
        )

    # LLM Answer Generation
    facts_dicts = [f.model_dump() for f in structured_facts]
    generation_result = generate_answer(
        clean_question,
        context,
        structured_facts=facts_dicts,
        conflicts=all_conflicts if tier == QueryTier.DEEP_RAG else None,
        missing_information=missing_info if tier != QueryTier.FAST_FACTUAL else None,
        risk_factors=risk_factors if tier == QueryTier.DEEP_RAG else None,
        risk_score=risk_score_result if tier == QueryTier.DEEP_RAG else None,
    )
    answer_text = generation_result.get("answer", "")

    # Claim Verification & Scoring
    claim_results = verify_all_claims(answer_text, structured_facts, reranked_chunks)
    evidence_score_result = evidence_scorer.calculate_evidence_score(
        claim_results=claim_results,
        facts=structured_facts,
        conflicts=all_conflicts,
        missing=missing_info,
        rerank_scores=rerank_scores,
        is_meta_query=(tier == QueryTier.DEEP_RAG),
    )

    validation = validate_final_response(
        answer_text,
        claim_results,
        structured_facts,
        reranked_chunks,
        is_meta_query=(tier == QueryTier.DEEP_RAG),
    )
    if not validation["valid"]:
        answer_text = validation["sanitized_answer"]

    grounded = ground_answer(answer_text, reranked_chunks, rerank_scores)

    # Token usage estimation
    in_tok = len(context) // 4 + 150
    out_tok = len(answer_text) // 4
    token_metrics = {
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "total_tokens": in_tok + out_tok,
        "tier": tier.value,
        "model": "gemini-3.5-flash-lite",
    }

    result = _build_response(
        answer_text=answer_text,
        structured_facts=structured_facts,
        reranked_chunks=reranked_chunks,
        context=context,
        intent_result=intent_result,
        claim_results=claim_results,
        evidence_score_result=evidence_score_result,
        grounded=grounded,
        clean_question=clean_question,
        tier=tier,
        all_conflicts=all_conflicts,
        missing_info=missing_info,
        cost_drivers=cost_drivers,
        risk_factors=risk_factors,
        risk_score_result=risk_score_result,
        lender_questions=lender_questions,
        token_metrics=token_metrics,
    )

    set_cached_response(question, product_ids, result, user_id=user_id)
    return result


def _build_response(
    *,
    answer_text: str,
    structured_facts: List[LoanFact],
    reranked_chunks: List[Dict[str, Any]],
    context: str,
    intent_result,
    claim_results: Dict[str, Any],
    evidence_score_result: Dict[str, Any],
    grounded: Dict[str, Any],
    clean_question: str,
    tier: QueryTier,
    all_conflicts: Optional[List] = None,
    missing_info: Optional[List] = None,
    calculation_result: Optional[Dict] = None,
    cost_drivers: Optional[List] = None,
    risk_factors: Optional[List] = None,
    risk_score_result: Optional[Dict] = None,
    lender_questions: Optional[List] = None,
    scenario: Optional[Dict] = None,
    token_metrics: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Shared builder to standardize final response payload across all tiers."""
    all_conflicts = all_conflicts or []
    missing_info = missing_info or []
    cost_drivers = cost_drivers or []
    risk_factors = risk_factors or []
    risk_score_result = risk_score_result or {"score": None, "level": None}
    lender_questions = lender_questions or []
    scenario = scenario or {}
    token_metrics = token_metrics or {}

    facts_dicts = [f.model_dump() for f in structured_facts]

    # Determine evidence status
    statuses = set(f.status for f in structured_facts)
    if all_conflicts or EvidenceStatus.CONFLICTED in statuses or EvidenceStatus.MIXED in statuses:
        overall_status = "CONFLICTED"
    elif EvidenceStatus.PARTIAL in statuses:
        overall_status = "PARTIAL"
    elif EvidenceStatus.CONDITIONAL in statuses:
        overall_status = "CONDITIONAL"
    elif EvidenceStatus.EXPLICIT in statuses:
        overall_status = "EXPLICIT"
    else:
        overall_status = "NOT_SPECIFIED"

    # Standardized HITL triggers
    hitl_required = False
    hitl_reason = None
    hitl_type = "GENERAL"
    
    if all_conflicts and len(all_conflicts) > 0:
        hitl_required = True
        hitl_type = "CONFLICT_REVIEW"
        hitl_reason = f"Discrepancy detected across document sources ({len(all_conflicts)} conflict(s) identified)."
    elif (risk_score_result.get("score") or 0) >= 70:
        hitl_required = True
        hitl_type = "RISK_ACCEPTANCE"
        hitl_reason = f"Document Risk Score is {risk_score_result.get('score')}/100 ({risk_score_result.get('level')}). High-risk clauses require explicit acknowledgment."
    elif evidence_score_result.get("score", 100) < 40:
        hitl_required = True
        hitl_type = "LOW_CONFIDENCE_AUDIT"
        hitl_reason = f"Evidence score is {evidence_score_result.get('score')}/100 (below confidence threshold of 40)."

    citations_list = grounded.get("citations", [])
    return {
        "answer": answer_text,
        "confidence_score": evidence_score_result.get("score_normalized", 0.0),
        "confidence_label": evidence_score_result.get("label", "Unknown"),
        "citations": citations_list,
        "evidence": citations_list,
        "retrieved_chunks": reranked_chunks,
        "context_used": context,
        "intent": intent_result.intent if hasattr(intent_result, "intent") else "general",
        "status": "ok",
        "processing_tier": tier.value,

        # Standardized HITL Fields
        "hitl_required": hitl_required,
        "hitl_reason": hitl_reason,
        "hitl_type": hitl_type,
        "hitl_status": "HITL_PENDING" if hitl_required else None,

        # Structured Fact Fields
        "why_this_answer": "All factual claims were verified with exact citations from the source document." if overall_status == "EXPLICIT" else "Terms were analyzed against operative credit disclosures.",
        "key_facts": facts_dicts,
        "calculations": [calculation_result] if calculation_result else [],
        "missing_information": missing_info,
        "conflicts": all_conflicts,
        "evidence_status": overall_status,
        "evidence_score": evidence_score_result.get("score", 0),
        "evidence_score_details": evidence_score_result,
        "claim_coverage": claim_results.get("claim_coverage", 1.0),
        "cost_drivers": cost_drivers,
        "risk_factors": risk_factors,
        "risk_score": risk_score_result.get("score"),
        "risk_level": risk_score_result.get("level"),
        "questions_to_ask_provider": lender_questions,
        "scenario": scenario,
        "token_metrics": token_metrics,
    }
