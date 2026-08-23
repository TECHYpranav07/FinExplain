import re
from typing import List, Dict, Any, Tuple

def extract_citations(answer: str) -> List[Dict[str, Any]]:
    """Extract document, page, and section citations from the answer text."""
    # Look for patterns like [sample_loan.pdf, Page 1], [Page 3], 【Page 1.0】, [Doc A, Page 2, Section 2.1]
    pattern = r'[\[【](?:([^,\]】]+?),\s*)?(?:Page|p\.)\s*([\d.]+)(?:,\s*Section:?\s*([^\]】]+?))?[\]】]|\[Section\s*([\d.]+)\]|Page\s+(\d+)'
    citations = []
    for match in re.finditer(pattern, answer, re.IGNORECASE):
        doc = match.group(1)
        raw_page = match.group(2) or match.group(5)
        section = match.group(3) or match.group(4)
        if raw_page:
            try:
                page_int = int(float(raw_page))
                cit: Dict[str, Any] = {"page": page_int}
                if doc and not doc.lower().startswith("section"):
                    cit["document"] = doc.strip()
                if section:
                    cit["section"] = section.strip()
                citations.append(cit)
            except ValueError:
                pass
    return citations

def verify_citation(citation: Dict[str, Any], retrieved_chunks: List[Dict[str, Any]]) -> bool:
    """Check if a citation points to an actual retrieved chunk.
    
    FIN-007: Requires document_id + page match, not just page existence.
    """
    page_num = citation.get("page")
    if not page_num:
        return False  # FIN-007: No page specified = not verified (was True)
    
    cited_doc = citation.get("document")
    
    for chunk in retrieved_chunks:
        chunk_page = chunk.get("page_number") or chunk.get("page_num")
        if chunk_page != page_num:
            continue
        # If a document name was cited, require it to match
        if cited_doc:
            chunk_doc = chunk.get("document_name", "")
            if cited_doc.lower() not in chunk_doc.lower() and chunk_doc.lower() not in cited_doc.lower():
                continue
        # Page matches (and document matches if specified)
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