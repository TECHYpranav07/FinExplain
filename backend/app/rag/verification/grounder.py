import re
from typing import List, Dict, Any, Tuple, Optional

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
    rerank_scores: List[float],
    claim_results: Optional[Dict[str, Any]] = None,
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
    
    # Factor 3: Citation coverage. Prefer claim-level verification when the
    # verifier has already mapped each claim to a cited page.
    citations = extract_citations(answer)
    verified_claims = []
    if claim_results and claim_results.get("claims"):
        verified_claims = [
            claim for claim in claim_results["claims"]
            if claim.get("supported") and claim.get("citation_valid")
        ]
    if claim_results and claim_results.get("total_claims"):
        citation_coverage = len(verified_claims) / claim_results["total_claims"]
    elif citations:
        verified_citations = sum(1 for c in citations if verify_citation(c, retrieved_chunks))
        citation_coverage = verified_citations / len(citations)
    else:
        # If no citations, assume low coverage unless answer is very short
        citation_coverage = 0.3 if len(answer) > 50 else 0.8
    
    # Combine factors (weights: chunk 0.25, rerank 0.35, citation 0.40)
    confidence = (0.25 * chunk_factor) + (0.35 * avg_rerank) + (0.40 * citation_coverage)
    
    return min(max(confidence, 0.0), 1.0)


def _map_claims_to_citations(
    claim_results: Dict[str, Any],
    citations: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Expose an auditable claim -> citation -> evidence relationship."""
    mapped = []
    for claim in (claim_results or {}).get("claims", []):
        cited_page = claim.get("cited_page")
        matching = [
            citation for citation in citations
            if cited_page is not None and citation.get("page") == cited_page
        ]
        mapped.append({
            "claim": claim.get("claim", ""),
            "cited_page": cited_page,
            "cited_document": claim.get("cited_document"),
            "evidence_id": claim.get("evidence_id"),
            "supported": bool(claim.get("supported")),
            "citation_verified": bool(claim.get("citation_valid")),
            "citation": matching[0] if matching else None,
            "issues": claim.get("issues", []),
        })
    return mapped

def ground_answer(
    answer: str, 
    retrieved_chunks: List[Dict[str, Any]], 
    rerank_scores: List[float],
    claim_results: Optional[Dict[str, Any]] = None,
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
    confidence = calculate_confidence(answer, retrieved_chunks, rerank_scores, claim_results)
    claim_citations = _map_claims_to_citations(claim_results or {}, verified_citations)
    claim_citation_coverage = (
        sum(1 for claim in claim_citations if claim["supported"] and claim["citation_verified"])
        / len(claim_citations)
        if claim_citations else 0.0
    )
    
    return {
        "answer": answer,
        "citations": verified_citations,
        "confidence_score": confidence,
        "confidence_label": "High" if confidence >= 0.75 else "Medium" if confidence >= 0.50 else "Low",
        "citation_coverage": len(verified_citations) / max(len(citations), 1),
        "claim_citations": claim_citations,
        "claim_citation_coverage": claim_citation_coverage,
    }
