from typing import List, Dict, Any
import re

# Default token estimation (rough: 4 chars per token)
def estimate_tokens(text: str) -> int:
    return len(text) // 4

def chunk_hierarchical(
    pages: List[Dict[str, Any]], 
    child_token_size: int = 200, 
    parent_token_size: int = 800
) -> List[Dict[str, Any]]:
    """
    Creates hierarchical chunks:
    - Child chunks: small (200 tokens) for high-precision retrieval.
    - Parent chunks: larger (800 tokens) providing full context.
    
    Returns a list of chunks with metadata.
    """
    chunks = []
    chunk_id_counter = 0
    
    for page in pages:
        page_num = page["page_num"]
        text = page["text"]
        
        # Split text into sentences (rough split by periods/newlines)
        sentences = re.split(r'(?<=[.!?])\s+|(?<=\n)\s*', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Build child chunks
        current_child = ""
        current_child_tokens = 0
        child_chunks_for_page = []
        
        for sentence in sentences:
            sentence_tokens = estimate_tokens(sentence)
            
            if current_child_tokens + sentence_tokens > child_token_size and current_child:
                # Save current child chunk
                child_chunks_for_page.append({
                    "text": current_child.strip(),
                    "token_count": current_child_tokens,
                    "page_num": page_num,
                })
                current_child = sentence
                current_child_tokens = sentence_tokens
            else:
                current_child += " " + sentence
                current_child_tokens += sentence_tokens
        
        # Add the last child chunk
        if current_child:
            child_chunks_for_page.append({
                "text": current_child.strip(),
                "token_count": current_child_tokens,
                "page_num": page_num,
            })
        
        # Now build parent chunks by grouping child chunks
        parent_chunks = []
        current_parent_text = ""
        current_parent_tokens = 0
        parent_child_ids = []
        
        for i, child in enumerate(child_chunks_for_page):
            child_text = child["text"]
            child_tokens = child["token_count"]
            
            if current_parent_tokens + child_tokens > parent_token_size and current_parent_text:
                # Save parent chunk with its child ids
                parent_chunks.append({
                    "text": current_parent_text.strip(),
                    "token_count": current_parent_tokens,
                    "page_num": page_num,
                    "child_indices": parent_child_ids
                })
                current_parent_text = child_text
                current_parent_tokens = child_tokens
                parent_child_ids = [i]
            else:
                current_parent_text += "\n\n" + child_text
                current_parent_tokens += child_tokens
                parent_child_ids.append(i)
        
        if current_parent_text:
            parent_chunks.append({
                "text": current_parent_text.strip(),
                "token_count": current_parent_tokens,
                "page_num": page_num,
                "child_indices": parent_child_ids
            })
        
        # Flatten structure: we store child chunks separately,
        # but we maintain parent_id for each child.
        # For simplicity, we just create a combined list of all chunks
        # with a 'type' field.
        for child in child_chunks_for_page:
            chunks.append({
                "type": "child",
                "text": child["text"],
                "token_count": child["token_count"],
                "page_num": child["page_num"],
                "parent_text": None,  # will be linked later
            })
        
        for parent in parent_chunks:
            chunks.append({
                "type": "parent",
                "text": parent["text"],
                "token_count": parent["token_count"],
                "page_num": parent["page_num"],
                "child_indices": parent["child_indices"],
            })
    
    return chunks

def get_parent_for_child(child_chunk: Dict[str, Any], all_chunks: List[Dict[str, Any]]) -> str:
    """
    Given a child chunk, find its parent text from the list of all chunks.
    """
    # This is a simplified lookup; in production, you'd store parent-child relationships explicitly.
    # We'll just match by page_num and similar text.
    for chunk in all_chunks:
        if chunk["type"] == "parent" and chunk["page_num"] == child_chunk["page_num"]:
            # Check if child text is contained in parent text
            if child_chunk["text"] in chunk["text"]:
                return chunk["text"]
    return child_chunk["text"]  # fallback