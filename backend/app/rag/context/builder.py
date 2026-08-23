"""
Context Builder and Deterministic Evidence Compressor for FinExplain.

Converts retrieved document chunks into clean, structured, and bounded evidence contexts
for LLM generation, reducing token consumption by up to 75% while maintaining citation trace.
"""

import hashlib
import re
from typing import List, Dict, Any, Optional


def estimate_tokens(text: str) -> int:
    return len(text) // 4


def compress_evidence_context(
    chunks: List[Dict[str, Any]],
    query: str,
    max_tokens: int = 500,
    max_passages: int = 3,
) -> str:
    """
    Extract 1-3 most salient evidence sentences from the top retrieved chunks
    using deterministic query-term overlap and numeric/financial regex matching.
    
    Produces a concise ~200-400 token structured context:
    [Product Name, Page X, Section Y]
    Exact cited clause text...
    """
    if not chunks:
        return ""

    stop_words = {
        "what", "is", "the", "a", "an", "of", "in", "for", "and", "or",
        "to", "on", "at", "by", "my", "me", "i", "how", "much", "this",
        "that", "are", "was", "be", "do", "does", "did", "will", "would",
        "can", "could", "if", "there", "with", "from", "about", "any", "please",
    }
    query_words = {
        w.lower() for w in re.findall(r'\w+', query)
        if len(w) > 2 and w.lower() not in stop_words
    }

    scored_passages = []
    seen_hashes = set()

    for chunk in chunks[:6]:
        metadata = chunk.get("metadata") or {}
        raw_text = chunk.get("text", "").strip()
        if not raw_text:
            continue

        page_num = chunk.get("page_number") or chunk.get("page_num") or metadata.get("page_num") or 1
        section = chunk.get("section_title") or metadata.get("section_title") or ""
        doc_name = chunk.get("document_name") or metadata.get("document_name") or ""
        product = chunk.get("product_name") or metadata.get("product_name") or ""
        display_name = doc_name or product or ""

        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', raw_text)
        for sent in sentences:
            sent_clean = sent.strip()
            if len(sent_clean) < 20:
                continue

            sent_words = set(re.findall(r'\w+', sent_clean.lower()))
            overlap = len(query_words & sent_words)
            
            # Boost sentences with numeric/financial terms (% or ₹ or Rs or numbers)
            has_financial_signal = bool(re.search(r'[\d%₹$]|(?:percent|fee|charge|rate|p\.a\.|annual)', sent_clean, re.I))
            score = overlap + (1.5 if has_financial_signal else 0.0)

            if score > 0:
                norm = " ".join(sent_clean.lower().split()[:15])
                text_hash = hashlib.md5(norm.encode("utf-8")).hexdigest()
                if text_hash not in seen_hashes:
                    seen_hashes.add(text_hash)
                    scored_passages.append({
                        "score": score,
                        "text": sent_clean,
                        "page": page_num,
                        "section": section,
                        "source_name": display_name,
                    })

    # Sort passages by relevance score
    scored_passages.sort(key=lambda x: x["score"], reverse=True)
    top_passages = scored_passages[:max_passages]

    if not top_passages and chunks:
        # Fallback to first chunk prefix
        first_chunk = chunks[0]
        meta = first_chunk.get("metadata") or {}
        p_name = first_chunk.get("document_name") or meta.get("document_name") or first_chunk.get("product_name") or meta.get("product_name") or ""
        p_num = first_chunk.get("page_number") or meta.get("page_num") or 1
        sec = first_chunk.get("section_title") or meta.get("section_title") or ""
        txt = first_chunk.get("text", "")[:400]
        header = f"[{p_name}, Page {p_num}, Section: {sec}]" if sec else (f"[{p_name}, Page {p_num}]" if p_name else f"[Page {p_num}]")
        return f"{header}\n{txt}"

    context_parts = []
    current_tokens = 0

    for p in top_passages:
        header_parts = []
        if p.get("source_name"):
            header_parts.append(p["source_name"])
        if p.get("page"):
            header_parts.append(f"Page {p['page']}")
        if p.get("section"):
            header_parts.append(f"Section: {p['section']}")

        formatted = f"[{', '.join(header_parts)}]\n{p['text']}" if header_parts else p["text"]
        tok = estimate_tokens(formatted)

        if current_tokens + tok <= max_tokens:
            context_parts.append(formatted)
            current_tokens += tok
        else:
            break

    return "\n\n---\n\n".join(context_parts) if context_parts else ""


def build_context(
    chunks: List[Dict[str, Any]], 
    max_tokens: int = 4000,
    max_chunks: Optional[int] = None,
) -> str:
    """Standard context builder for deep analysis queries."""
    if not chunks:
        return ""
    
    context_parts = []
    seen_hashes = set()
    current_tokens = 0
    chunks_added = 0
    
    for chunk in chunks:
        if max_chunks and chunks_added >= max_chunks:
            break

        metadata = chunk.get("metadata") or {}
        raw_text = chunk.get("text", "").strip()
        if not raw_text:
            continue

        norm_text = " ".join(raw_text.lower().split()[:30])
        text_hash = hashlib.md5(norm_text.encode("utf-8")).hexdigest()
        if text_hash in seen_hashes:
            continue
        seen_hashes.add(text_hash)

        header_parts = []
        doc_name = chunk.get("document_name") or metadata.get("document_name")
        product_name = chunk.get("product_name") or metadata.get("product_name")
        display_name = doc_name or product_name
        if display_name:
            header_parts.append(display_name)

        page_num = chunk.get("page_number") or chunk.get("page_num") or metadata.get("page_num")
        if page_num:
            header_parts.append(f"Page {page_num}")

        section_title = chunk.get("section_title") or metadata.get("section_title")
        if section_title:
            header_parts.append(f"Section: {section_title}")

        formatted_chunk = f"[{', '.join(header_parts)}]\n{raw_text}" if header_parts else raw_text
        chunk_tokens = estimate_tokens(formatted_chunk)
        
        if current_tokens + chunk_tokens <= max_tokens:
            context_parts.append(formatted_chunk)
            current_tokens += chunk_tokens
            chunks_added += 1
        else:
            remaining = max_tokens - current_tokens
            if remaining > 50:
                char_limit = remaining * 4
                truncated = formatted_chunk[:char_limit] + "..." if len(formatted_chunk) > char_limit else formatted_chunk
                context_parts.append(truncated)
                chunks_added += 1
            break
    
    return "\n\n---\n\n".join(context_parts) if context_parts else ""


def build_evidence_window(
    chunks: List[Dict[str, Any]],
    query: str,
    max_tokens: int = 1500,
    window_chars: int = 600,
) -> str:
    """Evidence window extractor."""
    return compress_evidence_context(chunks, query, max_tokens=max_tokens)
