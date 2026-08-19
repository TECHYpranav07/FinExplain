from typing import List, Dict, Any
from app.rag.verification.grounder import extract_citations, verify_citation

def execute_verification_tool(answer: str, retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Verify citations and grounding of a generated candidate answer."""
    citations = extract_citations(answer)
    verified = [c for c in citations if verify_citation(c, retrieved_chunks)]
    coverage = len(verified) / max(len(citations), 1) if citations else 1.0
    return {
        "total_citations": len(citations),
        "verified_citations": len(verified),
        "citation_coverage": coverage,
        "is_grounded": coverage >= 0.75
    }
