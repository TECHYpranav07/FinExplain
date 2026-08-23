"""
Structured Fact Store (LoanFact Store) for FinExplain.

Provides first-class persistent and in-memory storage for extracted loan facts.
Enables instant (<0.5ms in-memory, ~20ms DB/file) deterministic factual lookups,
completely bypassing vector search, BM25, and LLM calls for known financial terms.
"""

import os
import json
import logging
import time
from collections import OrderedDict
from typing import List, Dict, Any, Optional

from app.core.loan_categories import LoanFact, EvidenceStatus

logger = logging.getLogger(__name__)

# Persistent local fallback JSON file
_LOCAL_FACTS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "loan_facts.json")

# In-Memory L1 Cache for LoanFacts (product_id -> Dict[canonical_field, LoanFact])
_FACT_CACHE: OrderedDict[str, Dict[str, LoanFact]] = OrderedDict()
_MAX_CACHED_PRODUCTS = 100


def _load_local_facts():
    """Load persistent facts from local JSON backing store on startup."""
    global _FACT_CACHE
    if not os.path.exists(_LOCAL_FACTS_PATH):
        return
    try:
        with open(_LOCAL_FACTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for p_id, fields in data.items():
            if p_id not in _FACT_CACHE:
                _FACT_CACHE[p_id] = {}
            for k, f_dict in fields.items():
                fact = LoanFact(
                    category=f_dict.get("category", "other_fee"),
                    field=f_dict.get("field", "unknown"),
                    value=f_dict.get("value"),
                    unit=f_dict.get("unit"),
                    currency=f_dict.get("currency"),
                    condition=f_dict.get("condition"),
                    effective_date=f_dict.get("effective_date"),
                    source_document=f_dict.get("source_document"),
                    page=f_dict.get("page"),
                    section=f_dict.get("section"),
                    source_chunk_id=f_dict.get("source_chunk_id"),
                    source_text=f_dict.get("source_text"),
                    status=EvidenceStatus(f_dict.get("status", "EXPLICIT")),
                    confidence=float(f_dict.get("confidence", 0.98)),
                )
                _FACT_CACHE[p_id][k] = fact
    except Exception as e:
        logger.debug(f"[LoanFactStore] Error reading local facts file: {e}")


def _save_local_facts():
    """Save in-memory facts to persistent local JSON backing store."""
    try:
        os.makedirs(os.path.dirname(_LOCAL_FACTS_PATH), exist_ok=True)
        serializable = {}
        for p_id, fields in _FACT_CACHE.items():
            serializable[p_id] = {k: f.model_dump() for k, f in fields.items()}
        with open(_LOCAL_FACTS_PATH, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2, default=str)
    except Exception as e:
        logger.debug(f"[LoanFactStore] Error saving local facts file: {e}")


# Initialize cache from local storage on module import
_load_local_facts()


def _get_supabase():
    """Lazy import to avoid circular dependencies."""
    from app.db.supabase_client import get_supabase_client
    return get_supabase_client()


def normalize_field_name(field: str) -> str:
    """Normalize field aliases into canonical financial field keys."""
    f = field.lower().strip().replace(" ", "_").replace("-", "_")
    
    aliases = {
        "roi": "interest_rate",
        "rate_of_interest": "interest_rate",
        "annual_interest_rate": "interest_rate",
        "floating_rate": "interest_rate",
        "fixed_rate": "interest_rate",
        "processing_charges": "processing_fee",
        "admin_fee": "processing_fee",
        "origination_fee": "processing_fee",
        "documentation_charge": "documentation_fee",
        "doc_fee": "documentation_fee",
        "stamp_duty": "documentation_fee",
        "default_interest": "penal_interest",
        "penal_charge": "penal_interest",
        "penal_interest_rate": "penal_interest",
        "late_fee": "late_payment_fee",
        "delayed_payment_charge": "penal_interest",
        "ecs_bounce": "bounce_charge",
        "nach_bounce": "bounce_charge",
        "cheque_bounce": "bounce_charge",
        "foreclosure_fee": "foreclosure_charge",
        "foreclosure_penalty": "foreclosure_charge",
        "prepayment_fee": "prepayment_charge",
        "prepayment_penalty": "prepayment_charge",
        "duration": "tenure",
        "loan_term": "tenure",
        "repayment_period": "tenure",
        "principal": "loan_amount",
        "sanction_amount": "loan_amount",
        "sanctioned_amount": "loan_amount",
        "disbursed_amount": "loan_amount",
        "effective_rate": "apr",
        "annual_percentage_rate": "apr",
        "monthly_installment": "emi",
        "monthly_emi": "emi",
        "moratorium": "grace_period",
        "security": "collateral",
        "hypothecation": "collateral",
    }
    return aliases.get(f, f)


def get_fact(
    product_ids: List[str],
    field_name: str,
) -> Optional[LoanFact]:
    """
    Look up a single LoanFact by canonical field name.
    
    1. Checks L1 in-memory fact cache (<0.5ms).
    2. Checks PostgreSQL/Supabase database (~20ms).
    3. Caches result in L1.
    """
    canonical_field = normalize_field_name(field_name)
    
    # 1. Check L1 In-Memory Fact Cache
    for p_id in product_ids:
        if p_id in _FACT_CACHE:
            prod_facts = _FACT_CACHE[p_id]
            if canonical_field in prod_facts:
                logger.info(f"[LoanFactStore] ⚡ L1 Memory Fact HIT: {canonical_field} = {prod_facts[canonical_field].value} for product={p_id}")
                return prod_facts[canonical_field]

    # If no product_ids provided, search across all cached products
    if not product_ids and _FACT_CACHE:
        for p_id, prod_facts in _FACT_CACHE.items():
            if canonical_field in prod_facts:
                logger.info(f"[LoanFactStore] ⚡ L1 Memory Fact HIT (Global): {canonical_field} = {prod_facts[canonical_field].value}")
                return prod_facts[canonical_field]

    # 2. Query Database
    facts = lookup_facts(product_ids, field_category=canonical_field, limit=10)
    for fact in facts:
        fact_field = normalize_field_name(fact.field or fact.category)
        if fact_field == canonical_field:
            if product_ids:
                p_id = product_ids[0]
                if p_id not in _FACT_CACHE:
                    _FACT_CACHE[p_id] = {}
                _FACT_CACHE[p_id][canonical_field] = fact
                _save_local_facts()
            return fact

    return None


def get_all_facts(product_ids: List[str]) -> List[LoanFact]:
    """Retrieve all structured facts for the given products."""
    all_facts: List[LoanFact] = []
    
    all_in_cache = True
    for p_id in product_ids:
        if p_id in _FACT_CACHE:
            all_facts.extend(_FACT_CACHE[p_id].values())
        else:
            all_in_cache = False
            break

    if all_in_cache and all_facts:
        return all_facts

    if not product_ids and _FACT_CACHE:
        # Return facts from first cached product
        first_p = next(iter(_FACT_CACHE))
        return list(_FACT_CACHE[first_p].values())

    db_facts = lookup_facts(product_ids, limit=100)
    for fact in db_facts:
        p_id = getattr(fact, "product_id", None) or (product_ids[0] if product_ids else "default")
        if p_id not in _FACT_CACHE:
            _FACT_CACHE[p_id] = {}
        canonical = normalize_field_name(fact.field or fact.category)
        _FACT_CACHE[p_id][canonical] = fact

    _save_local_facts()
    return db_facts


def lookup_facts(
    product_ids: List[str],
    field_category: Optional[str] = None,
    limit: int = 50,
) -> List[LoanFact]:
    """Retrieve facts from the database."""
    try:
        client = _get_supabase()
        if not client:
            return []

        query = client.table("structured_facts").select("*")

        if product_ids:
            query = query.in_("product_id", product_ids)

        if field_category:
            canonical = normalize_field_name(field_category)
            query = query.or_(
                f"category.eq.{canonical},field.eq.{canonical},category.eq.{field_category},field.eq.{field_category}"
            )

        query = query.limit(limit)
        result = query.execute()

        if not result.data:
            return []

        facts: List[LoanFact] = []
        for row in result.data:
            try:
                fact = LoanFact(
                    category=row.get("category", "other_fee"),
                    field=row.get("field", "unknown"),
                    value=row.get("value"),
                    unit=row.get("unit"),
                    currency=row.get("currency"),
                    condition=row.get("condition"),
                    effective_date=row.get("effective_date"),
                    source_document=row.get("source_document"),
                    page=row.get("page"),
                    section=row.get("section"),
                    source_chunk_id=row.get("source_chunk_id"),
                    source_text=row.get("source_text"),
                    status=EvidenceStatus(row.get("status", "EXPLICIT")),
                    confidence=float(row.get("confidence", 0.98)),
                )
                facts.append(fact)
            except Exception as e:
                logger.debug(f"[LoanFactStore] Malformed row: {e}")
                continue

        return facts

    except Exception as e:
        logger.debug(f"[LoanFactStore] Lookup fallback: {e}")
        return []


def store_facts(
    facts: List[LoanFact],
    product_id: str,
    document_id: str,
) -> int:
    """
    Persist extracted LoanFacts to Supabase, Local Backing File, and L1 In-Memory Cache.
    """
    if not facts:
        return 0

    # 1. Update L1 In-Memory Cache
    if product_id not in _FACT_CACHE:
        if len(_FACT_CACHE) >= _MAX_CACHED_PRODUCTS:
            _FACT_CACHE.popitem(last=False)
        _FACT_CACHE[product_id] = {}

    for fact in facts:
        canonical = normalize_field_name(fact.field or fact.category)
        _FACT_CACHE[product_id][canonical] = fact

    # 2. Persist to Local JSON Backing Store
    _save_local_facts()

    # 3. Persist to PostgreSQL / Supabase
    try:
        client = _get_supabase()
        if not client:
            return len(facts)

        rows = []
        for fact in facts:
            rows.append({
                "product_id": product_id,
                "document_id": document_id,
                "category": fact.category,
                "field": fact.field,
                "value": fact.value,
                "unit": fact.unit,
                "currency": fact.currency,
                "condition": fact.condition,
                "page": fact.page,
                "section": fact.section,
                "source_text": fact.source_text,
                "status": fact.status.value if hasattr(fact.status, "value") else str(fact.status),
                "source_chunk_id": fact.source_chunk_id,
            })

        result = client.table("structured_facts").insert(rows).execute()
        stored = len(result.data) if result.data else len(rows)
        logger.info(f"[LoanFactStore] ✅ Stored {stored} facts for product={product_id}")
        return stored

    except Exception as e:
        logger.info(f"[LoanFactStore] Facts cached in L1 RAM + local storage ({len(facts)} facts): {e}")
        return len(facts)
