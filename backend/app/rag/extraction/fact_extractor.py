"""
Structured Loan Fact Extraction layer.

Uses the LLM to extract ``LoanFact`` objects from retrieved chunks.
This intermediate representation drives the calculation engine,
conflict detector, and evidence verifier — keeping the LLM out of
the numerical / deterministic decision path.
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional


from app.core.loan_categories import LoanFact, LOAN_CATEGORIES, EvidenceStatus
from app.rag.generation.generator import client

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# Extraction prompt — constrained to the fixed taxonomy
# -------------------------------------------------------------------------

FACT_EXTRACTION_PROMPT = """You are a loan-document fact extractor.

Given the document chunks below, extract every financial fact into a JSON array.

Each object MUST use this schema:
{{
  "category": "<one of: {categories}>",
  "field": "<specific name, e.g. processing_fee>",
  "value": "<extracted value or null>",
  "unit": "<percent | months | currency_code | null>",
  "currency": "<INR | USD | EUR | null>",
  "condition": "<condition text or null>",
  "effective_date": "<date string or null>",
  "page": <page number integer or null>,
  "section": "<section title or null>",
  "source_text": "<verbatim quote from the chunk>",
  "status": "<EXPLICIT | CONDITIONAL>"
}}

RULES:
1. Extract ONLY facts present in the text. Do NOT invent values.
2. If a fact has a condition (if, unless, after, before, subject to, etc.),
   set status = "CONDITIONAL" and put the condition text in "condition".
3. If the fact is unconditional, set status = "EXPLICIT".
4. Preserve the exact wording of conditions and qualifiers.
5. One fact per JSON object. Return a JSON array.
6. If no facts are found, return an empty array: []

CHUNKS:
{chunks_text}

Return ONLY the JSON array — no commentary.
"""


def extract_structured_facts(
    chunks: List[Dict[str, Any]],
    product_name: Optional[str] = None,
    document_name: Optional[str] = None,
) -> List[LoanFact]:
    """
    Extract structured ``LoanFact`` objects from a list of retrieved chunks.

    Parameters
    ----------
    chunks : list of chunk dicts (must have ``text``, ``page_number``/``page_num``, etc.)
    product_name : optional product name to attach to every extracted fact
    document_name : optional document filename to attach

    Returns
    -------
    list of ``LoanFact``
    """
    if not chunks:
        return []

    # Build the chunks text block
    parts = []
    for chunk in chunks:
        page = chunk.get("page_number") or chunk.get("page_num") or "?"
        section = chunk.get("section_title") or ""
        text = chunk.get("text", "")
        chunk_id = chunk.get("id") or chunk.get("chunk_id") or chunk.get("embedding_id") or ""
        p_name = chunk.get("product_name") or (chunk.get("metadata") or {}).get("product_name") or product_name or ""
        d_name = chunk.get("document_name") or (chunk.get("metadata") or {}).get("document_name") or document_name or ""
        
        header_parts = [f"Chunk {chunk_id}"]
        if p_name:
            header_parts.append(f"Product: {p_name}")
        if d_name:
            header_parts.append(f"Doc: {d_name}")
        header_parts.append(f"Page {page}")
        if section:
            header_parts.append(f"Section: {section}")
            
        header = f"[{', '.join(header_parts)}]"
        parts.append(f"{header}\n{text}")

    chunks_text = "\n\n---\n\n".join(parts)

    prompt = FACT_EXTRACTION_PROMPT.format(
        categories=", ".join(LOAN_CATEGORIES),
        chunks_text=chunks_text,
    )

    try:
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise financial fact extractor. Output only valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=2048,
        )
        raw = response.choices[0].message.content.strip()
        # Robust JSON array extraction (handles markdown fences, prefixes, etc.)
        match = re.search(r'\[\s*\{.*\}\s*\]', raw, re.DOTALL)

        if match:
            parsed = json.loads(match.group(0))
        elif "```" in raw:
            parts = raw.split("```")
            block = parts[1] if len(parts) > 1 else raw
            if block.startswith("json"):
                block = block[4:]
            parsed = json.loads(block.strip())
        else:
            parsed = json.loads(raw)

        if not isinstance(parsed, list):
            parsed = [parsed]

    except Exception as e:
        logger.warning(f"[FactExtractor] LLM extraction failed: {e} | Raw preview: {raw[:150] if 'raw' in locals() else 'None'}")
        return []


    # Convert raw dicts into LoanFact models
    facts: List[LoanFact] = []
    for item in parsed:
        try:
            # Map the fact back to its source chunk before applying metadata.
            # Page numbers can repeat across documents, so source text is the
            # strongest signal for multi-document comparisons.
            source_chunk = _find_source_chunk(
                chunks, item.get("page"), item.get("source_text")
            )
            chunk_id = _chunk_id(source_chunk)
            source_page = item.get("page")
            source_section = item.get("section")
            source_document = document_name
            if source_chunk:
                source_page = source_page or source_chunk.get("page_number") or source_chunk.get("page_num")
                source_section = source_section or source_chunk.get("section_title")
                source_document = (
                    source_chunk.get("document_name")
                    or (source_chunk.get("metadata") or {}).get("document_name")
                    or source_document
                )
            fact = LoanFact(
                category=item.get("category", "other_fee"),
                field=item.get("field", item.get("category", "unknown")),
                value=str(item["value"]) if item.get("value") is not None else None,
                unit=item.get("unit"),
                currency=item.get("currency"),
                condition=item.get("condition"),
                effective_date=item.get("effective_date"),
                source_document=source_document,
                page=source_page,
                section=source_section,
                source_chunk_id=chunk_id,
                source_text=item.get("source_text"),
                status=EvidenceStatus(item.get("status", "EXPLICIT")),
                confidence=0.8,  # default — refined later by verifier
            )
            facts.append(fact)
        except Exception as parse_err:
            logger.debug(f"[FactExtractor] Skipping malformed fact: {parse_err}")
            continue

    # Attach product / document names
    for fact in facts:
        if product_name and not fact.source_document:
            fact.source_document = product_name
        if document_name and not fact.source_document:
            fact.source_document = document_name

    return facts


def _chunk_id(chunk: Optional[Dict[str, Any]]) -> Optional[str]:
    """Return the canonical identifier used for a retrieved chunk."""
    if not chunk:
        return None
    return chunk.get("id") or chunk.get("chunk_id") or chunk.get("embedding_id")


def _find_source_chunk(
    chunks: List[Dict[str, Any]],
    page: Optional[int],
    source_text: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Best-effort match of a fact back to a specific chunk."""
    if page is None and not source_text:
        return None

    # Prefer exact source-text containment. This avoids attributing a fact to
    # the wrong document when two documents use the same page number.
    if source_text:
        for chunk in chunks:
            if source_text in chunk.get("text", ""):
                return chunk

    for chunk in chunks:
        chunk_page = chunk.get("page_number") or chunk.get("page_num")
        if page is not None and chunk_page == page:
            # Page match alone is acceptable
            return chunk

    return None
