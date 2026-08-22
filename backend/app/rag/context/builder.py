import hashlib
from typing import List, Dict, Any

def build_context(
    chunks: List[Dict[str, Any]], 
    max_tokens: int = 4000
) -> str:
    """
    Builds the final context for the LLM.
    FIN-023:
    - Preserves relevance ranking order from reranker (does NOT force parents ahead of top-ranked children)
    - Deduplicates identical or heavily overlapping text
    - Includes rich [Product Name, Page X, Section Y] headers per chunk
    - Safely budgets tokens up to max_tokens
    """
    if not chunks:
        return ""

    def estimate_tokens(text: str) -> int:
        return len(text) // 4
    
    context_parts = []
    seen_hashes = set()
    current_tokens = 0
    
    for chunk in chunks:
        metadata = chunk.get("metadata") or {}
        raw_text = chunk.get("text", "").strip()
        if not raw_text:
            continue

        # FIN-023: Text deduplication via normalized content hash
        norm_text = " ".join(raw_text.lower().split()[:30])
        text_hash = hashlib.md5(norm_text.encode("utf-8")).hexdigest()
        if text_hash in seen_hashes:
            continue
        seen_hashes.add(text_hash)

        # Build rich source header: [Product Name, Page X, Section Y]
        header_parts = []
        product_name = chunk.get("product_name") or metadata.get("product_name")
        if product_name:
            header_parts.append(product_name)

        page_num = (
            chunk.get("page_number")
            or chunk.get("page_num")
            or metadata.get("page_num")
        )
        if page_num:
            header_parts.append(f"Page {page_num}")

        section_title = (
            chunk.get("section_title")
            or metadata.get("section_title")
        )
        if section_title:
            header_parts.append(f"Section: {section_title}")

        document_name = chunk.get("document_name") or metadata.get("document_name")
        if document_name and not product_name:
            header_parts.insert(0, document_name)

        chunk_id = chunk.get("id") or chunk.get("chunk_id")
        if chunk_id:
            header_parts.append(f"Chunk: {chunk_id[:8]}")

        formatted_chunk = f"[{', '.join(header_parts)}]\n{raw_text}" if header_parts else raw_text
        chunk_tokens = estimate_tokens(formatted_chunk)
        
        # Check if we can add this chunk
        if current_tokens + chunk_tokens <= max_tokens:
            context_parts.append(formatted_chunk)
            current_tokens += chunk_tokens
        else:
            # Try to fit remaining space
            remaining = max_tokens - current_tokens
            if remaining > 50:
                char_limit = remaining * 4
                truncated = formatted_chunk[:char_limit] + "..." if len(formatted_chunk) > char_limit else formatted_chunk
                context_parts.append(truncated)
            break
    
    if not context_parts:
        return ""
    
    return "\n\n---\n\n".join(context_parts)
