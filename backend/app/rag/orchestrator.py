from app.rag.retrieval.hybrid_retriever import hybrid_search
from app.rag.retrieval.reranker import rerank_chunks
from app.rag.context.builder import build_context
from app.rag.generation.generator import generate_answer
from app.rag.verification.grounder import ground_answer
from typing import List, Dict, Any

def process_query(
    question: str,
    product_ids: List[str],
    max_retrieval: int = 30,
    max_context_tokens: int = 4000
) -> Dict[str, Any]:
    """
    Full RAG pipeline:
    1. Hybrid retrieval (Dense + BM25 + RRF)
    2. Reranking (Cross-encoder)
    3. Context building
    4. LLM generation
    5. Grounding & verification
    """
    
    # Step 1: Hybrid retrieval
    retrieved_chunks = hybrid_search(question, product_ids, top_k=max_retrieval)
    
    if not retrieved_chunks:
        return {
            "answer": "No relevant information found in the provided documents.",
            "confidence_score": 0.0,
            "confidence_label": "No Evidence",
            "citations": [],
            "retrieved_chunks": []
        }
    
    # Step 2: Rerank
    reranked_chunks = rerank_chunks(question, retrieved_chunks, top_k=10)
    
    # Extract rerank scores for confidence calculation
    rerank_scores = [chunk.get("rerank_score", 0.5) for chunk in reranked_chunks]
    
    # Step 3: Build context
    context = build_context(reranked_chunks, max_tokens=max_context_tokens)
    
    if not context:
        return {
            "answer": "Unable to build context from retrieved information.",
            "confidence_score": 0.0,
            "confidence_label": "No Evidence",
            "citations": [],
            "retrieved_chunks": reranked_chunks
        }
    
    # Step 4: Generate answer
    generation_result = generate_answer(question, context)
    
    if "error" in generation_result:
        return {
            "answer": generation_result["answer"],
            "confidence_score": 0.0,
            "confidence_label": "Error",
            "citations": [],
            "retrieved_chunks": reranked_chunks
        }
    
    # Step 5: Grounding & verification
    grounded_result = ground_answer(
        generation_result["answer"],
        reranked_chunks,
        rerank_scores
    )
    
    # Add additional metadata
    grounded_result["retrieved_chunks"] = reranked_chunks
    grounded_result["context_used"] = context
    
    return grounded_result