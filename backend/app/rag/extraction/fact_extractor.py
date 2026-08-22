"""
Structured Loan Fact Extraction layer.

Extracts ``LoanFact`` objects from retrieved chunks using fast deterministic
pattern matching with LLM fallback. This intermediate representation drives the
calculation engine, conflict detector, and evidence verifier — keeping the LLM out of
the numerical / deterministic decision path while ensuring 0 token waste for standard queries.
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


def _extract_heuristic_facts(
    chunks: List[Dict[str, Any]],
    product_name: Optional[str] = None,
    document_name: Optional[str] = None,
) -> List[LoanFact]:
    """
    Extract standard financial facts from chunks using deterministic pattern matching.
    Takes <1ms and 0 LLM tokens.
    """
    facts: List[LoanFact] = []
    seen_keys = set()

    for chunk in chunks:
        text = chunk.get("text", "")
        page = chunk.get("page_number") or chunk.get("page_num") or 1
        section = chunk.get("section_title") or "General Terms"
        chunk_id = chunk.get("id") or chunk.get("chunk_id") or chunk.get("embedding_id") or ""
        doc_name = (
            chunk.get("document_name")
            or (chunk.get("metadata") or {}).get("document_name")
            or document_name
            or product_name
        )

        # 1. Interest rate
        rate_matches = re.finditer(
            r"(?:interest\s+rate|rate\s+of\s+interest|roi)\s*(?:is|of|:)?\s*(\d+(?:\.\d+)?)\s*%",
            text,
            re.IGNORECASE,
        )
        for m in rate_matches:
            val = m.group(1)
            key = f"interest_rate_{val}_{page}"
            if key not in seen_keys:
                seen_keys.add(key)
                condition = "fixed" if "fixed" in text.lower() else ("floating" if "floating" in text.lower() else None)
                facts.append(
                    LoanFact(
                        category="interest_rate",
                        field="interest_rate",
                        value=val,
                        unit="percent",
                        condition=condition,
                        source_document=doc_name,
                        page=int(page) if str(page).isdigit() else 1,
                        section=section,
                        source_chunk_id=str(chunk_id),
                        source_text=m.group(0),
                        status=EvidenceStatus.EXPLICIT,
                        confidence=0.95,
                    )
                )

        # 2. Loan Amount
        amount_matches = re.finditer(
            r"(?:loan\s+amount|principal\s+amount|sanctioned\s+amount|facility\s+amount)\s*(?:is|of|:)?\s*(?:INR|Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
            text,
            re.IGNORECASE,
        )
        for m in amount_matches:
            val = m.group(1).replace(",", "")
            key = f"loan_amount_{val}_{page}"
            if key not in seen_keys and len(val) >= 3:
                seen_keys.add(key)
                facts.append(
                    LoanFact(
                        category="loan_amount",
                        field="loan_amount",
                        value=val,
                        unit="INR",
                        currency="INR",
                        source_document=doc_name,
                        page=int(page) if str(page).isdigit() else 1,
                        section=section,
                        source_chunk_id=str(chunk_id),
                        source_text=m.group(0),
                        status=EvidenceStatus.EXPLICIT,
                        confidence=0.95,
                    )
                )

        # 3. Tenure
        tenure_matches = re.finditer(
            r"(?:tenure|period|repayment\s+period|loan\s+period)\s*(?:is|of|:)?\s*(\d+)\s*(months|years|yrs|month|year)",
            text,
            re.IGNORECASE,
        )
        for m in tenure_matches:
            val = m.group(1)
            unit = m.group(2).lower()
            key = f"loan_tenure_{val}_{unit}_{page}"
            if key not in seen_keys:
                seen_keys.add(key)
                facts.append(
                    LoanFact(
                        category="loan_tenure",
                        field="loan_tenure",
                        value=f"{val} {unit}",
                        unit=unit,
                        source_document=doc_name,
                        page=int(page) if str(page).isdigit() else 1,
                        section=section,
                        source_chunk_id=str(chunk_id),
                        source_text=m.group(0),
                        status=EvidenceStatus.EXPLICIT,
                        confidence=0.95,
                    )
                )

        # 4. Processing Fee
        proc_matches = re.finditer(
            r"(?:processing\s+fee|origination\s+fee)\s*(?:is|of|:)?\s*(?:INR|Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)\s*(%|INR|Rs\.?|₹|\$)?",
            text,
            re.IGNORECASE,
        )
        for m in proc_matches:
            val = m.group(1).replace(",", "")
            unit = "percent" if m.group(2) == "%" else "INR"
            key = f"processing_fee_{val}_{page}"
            if key not in seen_keys:
                seen_keys.add(key)
                facts.append(
                    LoanFact(
                        category="processing_fee",
                        field="processing_fee",
                        value=val,
                        unit=unit,
                        source_document=doc_name,
                        page=int(page) if str(page).isdigit() else 1,
                        section=section,
                        source_chunk_id=str(chunk_id),
                        source_text=m.group(0),
                        status=EvidenceStatus.EXPLICIT,
                        confidence=0.95,
                    )
                )

        # 5. Documentation Fee
        doc_fee_matches = re.finditer(
            r"(?:documentation\s+fee|doc\s+fee)\s*(?:is|of|:)?\s*(?:INR|Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)\s*(%|INR|Rs\.?|₹|\$)?",
            text,
            re.IGNORECASE,
        )
        for m in doc_fee_matches:
            val = m.group(1).replace(",", "")
            unit = "percent" if m.group(2) == "%" else "INR"
            key = f"documentation_fee_{val}_{page}"
            if key not in seen_keys:
                seen_keys.add(key)
                facts.append(
                    LoanFact(
                        category="documentation_fee",
                        field="documentation_fee",
                        value=val,
                        unit=unit,
                        source_document=doc_name,
                        page=int(page) if str(page).isdigit() else 1,
                        section=section,
                        source_chunk_id=str(chunk_id),
                        source_text=m.group(0),
                        status=EvidenceStatus.EXPLICIT,
                        confidence=0.95,
                    )
                )

        # 6. Monthly EMI
        emi_matches = re.finditer(
            r"(?:monthly\s+emi|emi|monthly\s+installment)\s*(?:is|of|:)?\s*(?:INR|Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
            text,
            re.IGNORECASE,
        )
        for m in emi_matches:
            val = m.group(1).replace(",", "")
            key = f"monthly_emi_{val}_{page}"
            if key not in seen_keys and len(val) >= 3:
                seen_keys.add(key)
                facts.append(
                    LoanFact(
                        category="monthly_emi",
                        field="monthly_emi",
                        value=val,
                        unit="INR",
                        currency="INR",
                        source_document=doc_name,
                        page=int(page) if str(page).isdigit() else 1,
                        section=section,
                        source_chunk_id=str(chunk_id),
                        source_text=m.group(0),
                        status=EvidenceStatus.EXPLICIT,
                        confidence=0.95,
                    )
                )

        # 7. Late Payment Fee / Penal Charges
        late_matches = re.finditer(
            r"(?:late\s+payment\s+fee|late\s+fee|penal\s+charges?)\s*(?:is|of|:)?\s*(?:INR|Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)\s*(%|INR|Rs\.?|₹|\$)?",
            text,
            re.IGNORECASE,
        )
        for m in late_matches:
            val = m.group(1).replace(",", "")
            key = f"late_payment_{val}_{page}"
            if key not in seen_keys:
                seen_keys.add(key)
                is_cond = any(c in text.lower() for c in ("illustrative", "subject to", "discretion", "policy"))
                facts.append(
                    LoanFact(
                        category="late_payment",
                        field="late_payment_fee",
                        value=val,
                        unit="INR",
                        condition="Illustrative only; subject to lender policy" if is_cond else None,
                        source_document=doc_name,
                        page=int(page) if str(page).isdigit() else 1,
                        section=section,
                        source_chunk_id=str(chunk_id),
                        source_text=m.group(0),
                        status=EvidenceStatus.CONDITIONAL if is_cond else EvidenceStatus.EXPLICIT,
                        confidence=0.95,
                    )
                )

        # 8. Prepayment / Foreclosure Charge
        prep_matches = re.finditer(
            r"(?:prepayment\s+charge|foreclosure\s+charge|prepayment\s+penalty)\s*(?:is|of|:)?\s*(?:INR|Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)\s*(%|INR|Rs\.?|₹|\$)?",
            text,
            re.IGNORECASE,
        )
        for m in prep_matches:
            val = m.group(1).replace(",", "")
            unit = "percent" if m.group(2) == "%" else "INR"
            key = f"prepayment_{val}_{page}"
            if key not in seen_keys:
                seen_keys.add(key)
                is_cond = any(c in text.lower() for c in ("illustrative", "subject to", "discretion", "policy", "principal"))
                facts.append(
                    LoanFact(
                        category="prepayment",
                        field="prepayment_charge",
                        value=val,
                        unit=unit,
                        condition="of outstanding principal; Illustrative only" if is_cond else None,
                        source_document=doc_name,
                        page=int(page) if str(page).isdigit() else 1,
                        section=section,
                        source_chunk_id=str(chunk_id),
                        source_text=m.group(0),
                        status=EvidenceStatus.CONDITIONAL if is_cond else EvidenceStatus.EXPLICIT,
                        confidence=0.95,
                    )
                )

    return facts


def extract_structured_facts(
    chunks: List[Dict[str, Any]],
    product_name: Optional[str] = None,
    document_name: Optional[str] = None,
) -> List[LoanFact]:
    """
    Extract structured ``LoanFact`` objects from a list of retrieved chunks.
    First runs ultra-fast heuristic extraction (<1ms). If no facts matched,
    uses the LLM as fallback.
    """
    if not chunks:
        return []

    # 1. Fast deterministic extraction
    heuristic_facts = _extract_heuristic_facts(chunks, product_name=product_name, document_name=document_name)
    if heuristic_facts:
        logger.info(f"[FactExtractor] Fast heuristic extracted {len(heuristic_facts)} facts in <1ms (0 LLM tokens)")
        return heuristic_facts

    # 2. LLM fallback only if heuristics find 0 facts
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

        # Try to parse JSON (handle markdown fences if present)
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        parsed: list = json.loads(raw)

    except Exception as e:
        logger.warning(f"[FactExtractor] LLM extraction failed: {e}")
        return []

    # Convert raw dicts into LoanFact models
    facts: List[LoanFact] = []
    for item in parsed:
        try:
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
                confidence=0.8,
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

    if source_text:
        for chunk in chunks:
            if source_text in chunk.get("text", ""):
                return chunk

    for chunk in chunks:
        chunk_page = chunk.get("page_number") or chunk.get("page_num")
        if page is not None and chunk_page == page:
            return chunk

    return None
