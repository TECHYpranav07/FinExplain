from typing import List, Dict, Any

def build_context(
    chunks: List[Dict[str, Any]], 
    max_tokens: int = 4000
) -> str:
    """
    Builds the final context for the LLM.
    - Prioritizes Parent chunks over Child chunks (better context).
    - Includes [Product Name, Page X, Section Y] headers per chunk.
    - Truncates intelligently to max_tokens.
    """
    if not chunks:
        return ""

    # Helper to estimate tokens (rough: 4 chars = 1 token)
    def estimate_tokens(text: str) -> int:
        return len(text) // 4
    
    context_parts = []
    current_tokens = 0
    
    # We want to prioritize Parent chunks for better context
    # Sort: put parent chunks first, then child chunks (for diversity)
    sorted_chunks = sorted(chunks, key=lambda x: 0 if x.get("chunk_type") == "parent" else 1)
    
    for chunk in sorted_chunks:
        metadata = chunk.get("metadata") or {}
        text = chunk.get("text", "")

        # If we have a parent_text stored in metadata, use that instead for better context
        if "parent_text" in chunk and chunk["parent_text"]:
            text = chunk["parent_text"]

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

        if header_parts:
            header = f"[{', '.join(header_parts)}]"
            text = f"{header}\n{text}"
        
        chunk_tokens = estimate_tokens(text)
        
        # Check if we can add this chunk
        if current_tokens + chunk_tokens <= max_tokens:
            context_parts.append(text)
            current_tokens += chunk_tokens
        else:
            # Try to truncate to fit remaining space
            remaining = max_tokens - current_tokens
            if remaining > 50:  # Only include if at least 50 tokens fit
                # Estimate character limit
                char_limit = remaining * 4
                truncated = text[:char_limit] + "..." if len(text) > char_limit else text
                context_parts.append(truncated)
            break
    
    # If no context could be built, return empty
    if not context_parts:
        return ""
    
    return "\n\n---\n\n".join(context_parts)
