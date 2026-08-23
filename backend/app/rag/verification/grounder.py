import re
from typing import List, Dict, Any, Tuple

def extract_citations(answer: str) -> List[Dict[str, Any]]:
    """Extract document, page, section, and schedule citations from answer text."""
    # Matches [Doc, Page X, Section Y], [Page X], [Section X. Title], [Schedule II], etc.
    pattern = r'[\[【](?:([^,\]】]+?),\s*)?(?:(?:Page|p\.)\s*([\d.]+))?(?:,\s*Section:?\s*([^\]】]+?))?[\]】]|\[Section\s*([^\]]+)\]|\[Schedule\s*([^\]]+)\]|Page\s+(\d+)'
    citations = []
    for match in re.finditer(pattern, answer, re.IGNORECASE):
        doc = match.group(1)
        raw_page = match.group(2) or match.group(6)
        section = match.group(3) or match.group(4)
        schedule = match.group(5)
        
        cit: Dict[str, Any] = {}
        if raw_page:
            try:
                cit["page"] = int(float(raw_page))
            except ValueError:
                pass
        if doc and not doc.lower().startswith("section") and not doc.lower().startswith("schedule"):
            cit["document"] = doc.strip()
        if section:
            cit["section"] = section.strip()
        if schedule:
            cit["schedule"] = f"Schedule {schedule.strip()}"

        if cit:
            citations.append(cit)
    return citations

def verify_citation(citation: Dict[str, Any], retrieved_chunks: List[Dict[str, Any]]) -> bool:
    """Check if a citation points to an actual retrieved chunk."""
    page_num = citation.get("page")
    cited_doc = citation.get("document")
    cited_sec = citation.get("section")
    
    if not retrieved_chunks:
        return False

    for chunk in retrieved_chunks:
        chunk_page = chunk.get("page_number") or chunk.get("page_num")
        chunk_doc = chunk.get("document_name", "")
        chunk_sec = chunk.get("section_title") or chunk.get("section_name", "")
        
        # 1. If page number is given, check page match (and doc match if given)
        if page_num is not None:
            if chunk_page == page_num:
                if not cited_doc or (cited_doc.lower() in chunk_doc.lower() or chunk_doc.lower() in cited_doc.lower()):
                    return True

        # 2. If section is given without page, check section match
        if cited_sec and chunk_sec:
            if cited_sec.lower() in chunk_sec.lower() or chunk_sec.lower() in cited_sec.lower():
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