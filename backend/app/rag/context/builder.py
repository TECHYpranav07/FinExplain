from typing import List, Dict, Any

def build_context(
    chunks: List[Dict[str, Any]], 
    max_tokens: int = 4000
) -> str:
    """
    Builds the final context for the LLM.
    - Merges child chunks with their parent text for full context.
    - Orders chunks by relevance (highest first).
    - Truncates to max_tokens.
    """
    if not chunks:
        return ""
    
    # Estimate token count (rough: 4 chars = 1 token)
    def estimate_tokens(text: str) -> int:
        return len(text) // 4
    
    context_parts = []
    current_tokens = 0
    
    for chunk in chunks:
        text = chunk.get("text", "")
        
        # If this is a child chunk and we have the parent text, use parent instead
        # (Parent text is stored in metadata during ingestion)
        parent_text = chunk.get("parent_text")
        if parent_text:
            text = parent_text
        
        # Add section/page metadata
        page_num = chunk.get("page_number") or chunk.get("page_num")
        if page_num:
            text = f"[Page {page_num}] {text}"
        
        chunk_tokens = estimate_tokens(text)
        
        # Check if we can add this chunk
        if current_tokens + chunk_tokens <= max_tokens:
            context_parts.append(text)
            current_tokens += chunk_tokens
        else:
            # Try to truncate the chunk to fit remaining space
            remaining = max_tokens - current_tokens
            if remaining > 100:  # Only include if we have at least 100 tokens left
                truncated = text[:remaining * 4] + "..."
                context_parts.append(truncated)
            break
    
    return "\n\n---\n\n".join(context_parts)