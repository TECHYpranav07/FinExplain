import re
from typing import List, Dict, Any, Tuple

def extract_citations(answer: str) -> List[str]:
    """Extract page/section citations from the answer text."""
    # Look for patterns like [Page 3], [Section 2.1], [Page 5, Section 3]
    pattern = r'\[Page\s*(\d+)(?:,\s*Section\s*([\d.]+))?\]|\[Section\s*([\d.]+)\]|\[p\.\s*(\d+)\]'
    matches = re.findall(pattern, answer)
    citations = []
    for match in matches:
        page = match[0] or match[3]
        section = match[1] or match[2]
        if page:
            if section:
                citations.append({"page": int(page), "section": section})
            else:
                citations.append({"page": int(page)})
    return citations

def verify_citation(citation: Dict[str, Any], retrieved_chunks: List[Dict[str, Any]]) -> bool:
    """Check if a citation points to an actual retrieved chunk."""
    page_num = citation.get("page")
    if not page_num:
        return True  # No page specified, assume verified
    
    for chunk in retrieved_chunks:
        chunk_page = chunk.get("page_number") or chunk.get("page_num")
        if chunk_page == page_num:
            return True
    return False

def calculate_confidence(
    answer: str, 
    retrieved_chunks: List[Dict[str, Any]], 
    rerank_scores: List[float]
) -> float:
    """
    Calculate confidence score (0.0 - 1.0) based on:
    - Number of retrieved chunks
    - Average rerank score
    - Citation coverage
    - Completeness
    """
    if not retrieved_chunks:
        return 0.0
    
    # Factor 1: Chunk count (cap at 5)
    chunk_factor = min(len(retrieved_chunks) / 5, 1.0)
    
    # Factor 2: Average rerank score (if available)
    avg_rerank = sum(rerank_scores) / len(rerank_scores) if rerank_scores else 0.5
    
    # Factor 3: Citation coverage
    citations = extract_citations(answer)
    if citations:
        verified_citations = sum(1 for c in citations if verify_citation(c, retrieved_chunks))
        citation_coverage = verified_citations / len(citations)
    else:
        # If no citations, assume low coverage unless answer is very short
        citation_coverage = 0.3 if len(answer) > 50 else 0.8
    
    # Combine factors (weights: chunk 0.25, rerank 0.35, citation 0.40)
    confidence = (0.25 * chunk_factor) + (0.35 * avg_rerank) + (0.40 * citation_coverage)
    
    return min(max(confidence, 0.0), 1.0)

def ground_answer(
    answer: str, 
    retrieved_chunks: List[Dict[str, Any]], 
    rerank_scores: List[float]
) -> Dict[str, Any]:
    """
    Verifies every claim in the answer against the retrieved chunks.
    Returns a grounded answer with citations and confidence score.
    """
    # Extract citations from the answer
    citations = extract_citations(answer)
    
    # Verify each citation
    verified_citations = []
    for citation in citations:
        is_verified = verify_citation(citation, retrieved_chunks)
        verified_citations.append({
            **citation,
            "verified": is_verified
        })
    
    # Calculate confidence
    confidence = calculate_confidence(answer, retrieved_chunks, rerank_scores)
    
    return {
        "answer": answer,
        "citations": verified_citations,
        "confidence_score": confidence,
        "confidence_label": "High" if confidence >= 0.75 else "Medium" if confidence >= 0.50 else "Low",
        "citation_coverage": len(verified_citations) / max(len(citations), 1)
    }