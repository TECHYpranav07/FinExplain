from typing import List, Dict, Any
import re

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
        doc_id = chunk.get("document_id") or chunk.get("metadata", {}).get("document_id")
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