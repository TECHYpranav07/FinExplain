"""
Conflict detection for FinExplain.

Two complementary detectors:
1. ``detect_conflicts(chunks)`` — original chunk-level numeric comparison
   (backward-compatible).
2. ``detect_fact_conflicts(facts)`` — new structured-fact-level comparison
   across different source documents, with category-aware logic.

Both are pure deterministic Python — no LLM calls.
"""

from typing import List, Dict, Any
import re

from app.core.loan_categories import LoanFact, EvidenceStatus, normalize_field_name


# ---------------------------------------------------------------------------
# 1. Original chunk-level conflict detector (backward compatible)
# ---------------------------------------------------------------------------

def detect_conflicts(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detect contradictions between retrieved chunks.
    Looks for conflicting values (e.g., 10.5% vs 11.5% APR).
    """
    conflicts = []
    
    # Extract numeric fields from chunks
    numeric_pattern = r'(\d+\.?\d*)\s*(%|\$|USD|EUR|GBP)?'
    
    # Group chunks by document/product
    chunk_map = {}
    for chunk in chunks:
        metadata = chunk.get("metadata") or {}
        doc_id = chunk.get("document_id") or metadata.get("document_id")
        if doc_id:
            if doc_id not in chunk_map:
                chunk_map[doc_id] = []
            chunk_map[doc_id].append(chunk)
    
    # Compare values across different documents
    if len(chunk_map) > 1:
        # Look for numeric values that differ significantly
        doc_texts = {}
        for doc_id, doc_chunks in chunk_map.items():
            text = " ".join([c.get("text", "") for c in doc_chunks])
            doc_texts[doc_id] = text
        
        # Simple conflict detection: find numbers that appear differently
        for doc1, text1 in doc_texts.items():
            for doc2, text2 in doc_texts.items():
                if doc1 >= doc2:
                    continue
                
                # Find numbers in both texts
                nums1 = re.findall(r'(\d+\.?\d*)\s*(%|\$|USD|EUR|GBP)?', text1)
                nums2 = re.findall(r'(\d+\.?\d*)\s*(%|\$|USD|EUR|GBP)?', text2)
                
                for n1, unit1 in nums1:
                    for n2, unit2 in nums2:
                        if unit1 == unit2 and unit1 in ["%", "$"]:
                            if abs(float(n1) - float(n2)) > 0.5:  # Significant difference
                                conflicts.append({
                                    "field": f"{unit1} value",
                                    "value_a": f"{n1}{unit1}",
                                    "value_b": f"{n2}{unit2}",
                                    "document_a": doc1,
                                    "document_b": doc2
                                })
    
    return conflicts


# ---------------------------------------------------------------------------
# 2. New structured-fact-level conflict detector
# ---------------------------------------------------------------------------

def _normalise_value(value: str | None) -> str | None:
    """Lowercase, strip whitespace, remove trailing % or currency symbols."""
    if value is None:
        return None
    v = value.strip().lower()
    # Remove common trailing units for comparison
    v = re.sub(r'[%$€₹£]', '', v).strip()
    return v if v else None


def detect_fact_conflicts(facts: List[LoanFact]) -> List[Dict[str, Any]]:
    """
    Compare structured ``LoanFact`` objects with the same
    ``(category, field)`` key across different source documents.

    Detects:
    - Value mismatches  (e.g. 1% vs 2%)
    - Currency mismatches (e.g. USD vs EUR)
    - Condition contradictions  (e.g. "waived" vs "applicable")

    Returns a list of conflict reports::

        [
            {
                "field": "processing_fee",
                "status": "MIXED",
                "conflict": True,
                "values": [
                    {"value": "1%", "document": "terms_2025.pdf", "page": 5, ...},
                    {"value": "2%", "document": "terms_2026.pdf", "page": 8, ...},
                ]
            },
            ...
        ]
    """
    # Group facts by (category, field)
    groups: Dict[tuple, List[LoanFact]] = {}
    for fact in facts:
        key = (normalize_field_name(fact.category), normalize_field_name(fact.field))
        groups.setdefault(key, []).append(fact)

    conflicts: List[Dict[str, Any]] = []

    for (category, field), group_facts in groups.items():
        if len(group_facts) < 2:
            continue

        # Compare every pair from different documents
        seen_pairs: set = set()
        for i, fa in enumerate(group_facts):
            for j, fb in enumerate(group_facts):
                if j <= i:
                    continue
                # Only flag conflicts across different source documents
                if fa.source_document and fb.source_document and fa.source_document == fb.source_document:
                    # Same document — could still be section-level conflict,
                    # but only flag if pages differ
                    if fa.page == fb.page:
                        continue

                pair_key = (id(fa), id(fb))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                is_conflict = False

                # Value mismatch
                norm_a = _normalise_value(fa.value)
                norm_b = _normalise_value(fb.value)
                if norm_a and norm_b and norm_a != norm_b:
                    is_conflict = True

                # Currency mismatch
                if fa.currency and fb.currency and fa.currency != fb.currency:
                    is_conflict = True

                # Condition contradiction (one says waived, other says applicable)
                cond_a = (fa.condition or "").lower()
                cond_b = (fb.condition or "").lower()
                waiver_terms = {"waived", "waiver", "exempt", "no charge", "nil", "zero"}
                applicable_terms = {"applicable", "applies", "charged", "payable"}
                a_waived = any(t in cond_a or t in (fa.value or "").lower() for t in waiver_terms)
                b_applicable = any(t in cond_b or t in (fb.value or "").lower() for t in applicable_terms)
                b_waived = any(t in cond_b or t in (fb.value or "").lower() for t in waiver_terms)
                a_applicable = any(t in cond_a or t in (fa.value or "").lower() for t in applicable_terms)
                if (a_waived and b_applicable) or (b_waived and a_applicable):
                    is_conflict = True

                if is_conflict:
                    conflicts.append({
                        "field": field,
                        "category": category,
                        "status": "MIXED",
                        "conflict": True,
                        "values": [
                            {
                                "value": fa.value,
                                "unit": fa.unit,
                                "currency": fa.currency,
                                "condition": fa.condition,
                                "document": fa.source_document,
                                "page": fa.page,
                                "section": fa.section,
                                "chunk_id": fa.source_chunk_id,
                            },
                            {
                                "value": fb.value,
                                "unit": fb.unit,
                                "currency": fb.currency,
                                "condition": fb.condition,
                                "document": fb.source_document,
                                "page": fb.page,
                                "section": fb.section,
                                "chunk_id": fb.source_chunk_id,
                            },
                        ],
                    })

    return conflicts
