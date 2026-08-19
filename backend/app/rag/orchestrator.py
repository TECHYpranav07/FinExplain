from app.rag.retrieval.hybrid_retriever import hybrid_search
from app.rag.retrieval.reranker import rerank_chunks
from app.rag.context.builder import build_context
from app.rag.generation.generator import generate_answer
from app.rag.verification.grounder import ground_answer
from app.rag.enhancement.intent_classifier import classify_intent
from app.rag.enhancement.query_rewriter import rewrite_query
from app.rag.enhancement.multi_query import generate_multi_queries
from app.rag.verification.conflict_detector import detect_conflicts
from app.rag.verification.confidence import calculate_confidence
from app.cache.query_cache import get_cached_response, set_cached_response
from typing import List, Dict, Any

def process_query(
    question: str,
    product_ids: List[str],
    max_retrieval: int = 30,
    max_context_tokens: int = 4000
) -> Dict[str, Any]:
    """
    Enhanced RAG pipeline with intent detection, query rewriting,
    conflict detection, and HILT escalation.
    """
    # Step 0: Check cache
    cached = get_cached_response(question, product_ids)
    if cached:
        return cached

    # Step 1: Classify intent
    intent_result = classify_intent(question)
    print(f"📊 Intent: {intent_result.intent}, Confidence: {intent_result.confidence}")

    # Step 2: Rewrite query
    rewritten_query = rewrite_query(question, intent_result.intent)
    print(f"✏️ Rewritten: {rewritten_query}")

    # Step 3: Generate multi-queries
    queries = generate_multi_queries(rewritten_query, num_queries=3)
    print(f"🔍 Multi-queries: {queries}")

    # Step 4: Hybrid retrieval (use first query for now)
    retrieved_chunks = hybrid_search(queries[0], product_ids, top_k=max_retrieval)

    if not retrieved_chunks:
        return {
            "answer": "No relevant information found.",
            "confidence_score": 0.0,
            "confidence_label": "No Evidence",
            "citations": [],
            "intent": intent_result.intent
        }

    # Step 5: Detect conflicts
    conflicts = detect_conflicts(retrieved_chunks)
    if conflicts:
        print(f"⚠️ Conflicts detected: {len(conflicts)}")

    # Step 6: Rerank
    reranked_chunks = rerank_chunks(queries[0], retrieved_chunks, top_k=10)
    rerank_scores = [c.get("rerank_score", 0.5) for c in reranked_chunks]

    # Step 7: Build context
    context = build_context(reranked_chunks, max_tokens=max_context_tokens)

    if not context:
        return {
            "answer": "Unable to build context.",
            "confidence_score": 0.0,
            "confidence_label": "No Evidence",
            "citations": [],
            "retrieved_chunks": reranked_chunks,
            "intent": intent_result.intent
        }

    # Step 8: Generate answer
    generation_result = generate_answer(question, context)

    if "error" in generation_result:
        return {
            "answer": generation_result["answer"],
            "confidence_score": 0.0,
            "confidence_label": "Error",
            "citations": [],
            "retrieved_chunks": reranked_chunks,
            "intent": intent_result.intent
        }

    # Step 9: Ground & verify
    grounded_result = ground_answer(
        generation_result["answer"],
        reranked_chunks,
        rerank_scores
    )

    # Step 10: Add metadata
    grounded_result["retrieved_chunks"] = reranked_chunks
    grounded_result["context_used"] = context
    grounded_result["intent"] = intent_result.intent
    grounded_result["conflicts"] = conflicts

    # Step 11: Calculate confidence (enhanced with conflict penalty)
    confidence_result = calculate_confidence(
        retrieved_chunks=reranked_chunks,
        rerank_scores=rerank_scores,
        citation_coverage=grounded_result.get("citation_coverage", 0.0),
        conflicts_detected=bool(conflicts)
    )
    grounded_result["confidence_score"] = confidence_result["score"]
    grounded_result["confidence_label"] = confidence_result["label"]

    # Step 12: Check if HILT escalation is needed (lazy import to avoid circular)
    if confidence_result["score"] < 0.4:
        from app.hilt.workflow import escalate_to_hilt
        hilt_result = escalate_to_hilt(question, product_ids)
        grounded_result["status"] = "hilt_escalated"
        grounded_result["hilt_info"] = hilt_result

    # Step 13: Cache
    set_cached_response(question, product_ids, grounded_result)

    return grounded_result