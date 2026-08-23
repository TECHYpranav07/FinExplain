from typing import List, Dict, Any, Optional
import re
import uuid

# Default token estimation (rough: 4 chars per token)
def estimate_tokens(text: str) -> int:
    return len(text) // 4


def _resolve_section_title(
    page_sections: List[Dict[str, Any]],
    text_position: int,
    page_text: str,
) -> Optional[str]:
    """
    Given a list of section headings detected on a page and a character
    position within the page text, return the most recent heading that
    appears before (or at) *text_position*.  If none is found, return None.
    """
    best_title: Optional[str] = None
    for sec in page_sections:
        title = sec.get("title", "")
        idx = page_text.find(title)
        if idx != -1 and idx <= text_position:
            best_title = title
    return best_title


def chunk_hierarchical(
    pages: List[Dict[str, Any]],
    child_token_size: int = 200,
    parent_token_size: int = 800,
    document_name: Optional[str] = None,
    product_name: Optional[str] = None,
    effective_date: Optional[str] = None,
    document_version: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Creates hierarchical chunks:
    - Child chunks: small (200 tokens) for high-precision retrieval.
    - Parent chunks: larger (800 tokens) providing full context.

    Each chunk carries rich metadata:
    - ``chunk_id``      – stable UUID
    - ``section_title`` – nearest heading from the page
    - ``document_name`` / ``product_name`` / ``effective_date`` / ``document_version``

    Returns a list of chunks with metadata.
    """
    chunks: List[Dict[str, Any]] = []

    for page in pages:
        page_num = page.get("page_num") or page.get("page_number", 1)
        text = page.get("text", "")
        raw_text = page.get("raw_text", text)
        page_sections = page.get("sections", [])
        page_tables = page.get("tables", [])

        child_chunks_for_page: List[Dict[str, Any]] = []

        # 1. Emit atomic chunks for structured tables first (preserves fee & condition columns)
        for t in page_tables:
            t_md = t.get("markdown", "")
            if not t_md:
                continue
            t_tokens = estimate_tokens(t_md)
            t_section = _resolve_section_title(page_sections, 0, text)
            child_chunks_for_page.append({
                "chunk_id": str(uuid.uuid4()),
                "text": f"[Structured Table - Page {page_num}]\n{t_md}",
                "token_count": t_tokens,
                "page_num": page_num,
                "section_title": t_section or "Schedule of Charges / Terms Table",
                "document_name": document_name,
                "product_name": product_name,
                "effective_date": effective_date,
                "document_version": document_version,
                "is_table": True,
            })

        # 2. Split narrative text into sentences
        # IMPORTANT: Do NOT strip conditional language ("if", "unless",
        # "subject to", etc.) — they are financially significant.
        sentences = re.split(r'(?<=[.!?])\s+|(?<=\n)\s*', raw_text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # Build child chunks for narrative text
        current_child = ""
        current_child_tokens = 0
        current_child_start_pos = 0  # char offset in page text

        for sentence in sentences:
            sentence_tokens = estimate_tokens(sentence)

            if current_child_tokens + sentence_tokens > child_token_size and current_child:
                # Save current child chunk
                section = _resolve_section_title(
                    page_sections, current_child_start_pos, raw_text
                )
                child_chunks_for_page.append({
                    "chunk_id": str(uuid.uuid4()),
                    "text": current_child.strip(),
                    "token_count": current_child_tokens,
                    "page_num": page_num,
                    "section_title": section,
                    "document_name": document_name,
                    "product_name": product_name,
                    "effective_date": effective_date,
                    "document_version": document_version,
                    "is_table": False,
                })
                current_child_start_pos = raw_text.find(sentence, current_child_start_pos)
                current_child = sentence
                current_child_tokens = sentence_tokens
            else:
                if not current_child:
                    current_child_start_pos = raw_text.find(sentence)
                current_child += " " + sentence
                current_child_tokens += sentence_tokens

        # Add the last child chunk
        if current_child:
            section = _resolve_section_title(
                page_sections, current_child_start_pos, raw_text
            )
            child_chunks_for_page.append({
                "chunk_id": str(uuid.uuid4()),
                "text": current_child.strip(),
                "token_count": current_child_tokens,
                "page_num": page_num,
                "section_title": section,
                "document_name": document_name,
                "product_name": product_name,
                "effective_date": effective_date,
                "document_version": document_version,
                "is_table": False,
            })

        # Now build parent chunks by grouping child chunks
        parent_chunks: List[Dict[str, Any]] = []
        current_parent_text = ""
        current_parent_tokens = 0
        parent_child_ids: List[str] = []
        parent_section: Optional[str] = None

        for child in child_chunks_for_page:
            child_text = child["text"]
            child_tokens = child["token_count"]

            if current_parent_tokens + child_tokens > parent_token_size and current_parent_text:
                parent_chunks.append({
                    "chunk_id": str(uuid.uuid4()),
                    "text": current_parent_text.strip(),
                    "token_count": current_parent_tokens,
                    "page_num": page_num,
                    "section_title": parent_section,
                    "child_ids": parent_child_ids,
                    "document_name": document_name,
                    "product_name": product_name,
                    "effective_date": effective_date,
                    "document_version": document_version,
                })
                current_parent_text = child_text
                current_parent_tokens = child_tokens
                parent_child_ids = [child["chunk_id"]]
                parent_section = child.get("section_title")
            else:
                current_parent_text += "\n\n" + child_text
                current_parent_tokens += child_tokens
                parent_child_ids.append(child["chunk_id"])
                if child.get("section_title"):
                    parent_section = child["section_title"]

        if current_parent_text:
            parent_chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "text": current_parent_text.strip(),
                "token_count": current_parent_tokens,
                "page_num": page_num,
                "section_title": parent_section,
                "child_ids": parent_child_ids,
                "document_name": document_name,
                "product_name": product_name,
                "effective_date": effective_date,
                "document_version": document_version,
            })

        # Map child_id -> parent_chunk_id
        child_to_parent_id = {}
        for parent in parent_chunks:
            for c_id in parent.get("child_ids", []):
                child_to_parent_id[c_id] = parent["chunk_id"]

        # Flatten structure with a 'type' field
        for child in child_chunks_for_page:
            chunks.append({
                "type": "child",
                "chunk_id": child["chunk_id"],
                "parent_chunk_id": child_to_parent_id.get(child["chunk_id"]),
                "text": child["text"],
                "token_count": child["token_count"],
                "page_num": child["page_num"],
                "section_title": child.get("section_title"),
                "document_name": document_name,
                "product_name": product_name,
                "effective_date": effective_date,
                "document_version": document_version,
                "is_table": child.get("is_table", False),
                "parent_text": None,
            })

        for parent in parent_chunks:
            chunks.append({
                "type": "parent",
                "chunk_id": parent["chunk_id"],
                "parent_chunk_id": None,
                "text": parent["text"],
                "token_count": parent["token_count"],
                "page_num": parent["page_num"],
                "section_title": parent.get("section_title"),
                "child_ids": parent.get("child_ids", []),
                "document_name": document_name,
                "product_name": product_name,
                "effective_date": effective_date,
                "document_version": document_version,
                "is_table": any(c.get("is_table") for c in child_chunks_for_page if c["chunk_id"] in parent.get("child_ids", [])),
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