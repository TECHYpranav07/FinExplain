"""
Backfill script to extract and populate LoanFacts for all existing products and documents.
"""

import sys
import os
import json
import logging

sys.path.insert(0, r"d:\Projects\fine-explain\backend")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

from app.db.supabase_client import get_supabase_client
from app.rag.extraction.fact_extractor import extract_structured_facts
from app.rag.extraction.structured_fact_store import store_facts


def backfill_all():
    client = get_supabase_client()
    if not client:
        logger.error("Supabase client unavailable")
        return

    # 1. Fetch all products
    res_prod = client.table("products").select("*").execute()
    products = res_prod.data or []
    logger.info(f"Found {len(products)} products to backfill")

    for prod in products:
        p_id = prod["id"]
        p_name = prod.get("name", "Loan Product")
        doc_id = prod.get("document_id")

        logger.info(f"--- Processing Product: {p_name} ({p_id}) ---")

        # 2. Fetch chunks for this product / document
        query = client.table("chunks").select("*")
        if doc_id:
            query = query.eq("document_id", doc_id)
        
        chunks_res = query.limit(20).execute()
        chunks = chunks_res.data or []

        if not chunks:
            # Try fetching without doc_id if empty
            chunks = client.table("chunks").select("*").limit(20).execute().data or []

        logger.info(f"Retrieved {len(chunks)} chunks for extraction")

        fact_chunks = [
            {
                "text": c.get("text", ""),
                "page_number": c.get("page_number", 1),
                "section_title": c.get("section_name") or "",
                "chunk_id": c.get("embedding_id", f"{p_id}_{idx}"),
                "document_name": p_name,
                "product_name": p_name,
            }
            for idx, c in enumerate(chunks)
        ]

        if not fact_chunks:
            continue

        # 3. Extract facts via LLM (one-time)
        logger.info(f"Extracting structured facts for '{p_name}'...")
        facts = extract_structured_facts(fact_chunks, product_name=p_name, document_name=p_name)
        logger.info(f"Extracted {len(facts)} facts: {[f.field for f in facts]}")

        # 4. Persist to LoanFactStore
        stored_count = store_facts(facts, product_id=p_id, document_id=doc_id or p_id)
        logger.info(f"✅ Successfully stored {stored_count} facts for '{p_name}'")


if __name__ == "__main__":
    backfill_all()
