"""
Two-Tier Cache Hierarchy (L1 In-Memory LRU + L2 Upstash Redis) for FinExplain.

Architecture:
  REQUEST -> L1 Memory (<0.5ms) -> HIT -> RETURN
               | (MISS)
               v
             L2 Redis (~80ms)  -> HIT -> Promote to L1 -> RETURN
               | (MISS)
               v
             RAG Pipeline -> Async Save to L1 & L2
"""

import hashlib
import json
import logging
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional

from app.cache.redis_client import redis_client
from app.core.config import settings

logger = logging.getLogger(__name__)

CACHE_TTL = 3600  # 1 hour in seconds
PIPELINE_VERSION = "v2.2-completeness-gate"

# L1 In-Memory LRU Cache (<0.5ms lookup)
_L1_MEMORY_CACHE: OrderedDict[str, tuple[float, Dict[str, Any]]] = OrderedDict()
_MAX_L1_ITEMS = 1000

# Background pool for non-blocking asynchronous L2 Redis saves
_cache_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="cache_writer")


def get_cache_key(
    query: str,
    product_ids: List[str],
    user_id: Optional[str] = None,
    doc_version: Optional[str] = None,
) -> str:
    """
    Generate a deterministic versioned cache key scoped by:
    tenant_id / user_scope / product_ids / doc_version / model / normalized_query.
    """
    product_str = "_".join(sorted(str(p) for p in product_ids))
    model_name = settings.active_llm_model
    user_str = str(user_id or "anon")
    version_str = str(doc_version or "v1")
    normalized_q = " ".join(query.strip().lower().split())
    
    unique_string = f"{PIPELINE_VERSION}:{user_str}:{settings.LLM_PROVIDER}:{model_name}:{version_str}:{normalized_q}:{product_str}"
    return f"finex:query:{hashlib.sha256(unique_string.encode()).hexdigest()}"


def get_cached_response(
    query: str,
    product_ids: List[str],
    user_id: Optional[str] = None,
    doc_version: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Check L1 Memory Cache first, then L2 Redis Cache.
    """
    key = get_cache_key(query, product_ids, user_id=user_id, doc_version=doc_version)

    # 1. Check L1 In-Memory Cache (<0.5ms)
    if key in _L1_MEMORY_CACHE:
        ts, data = _L1_MEMORY_CACHE[key]
        if time.time() - ts < CACHE_TTL:
            # Move to end for LRU
            _L1_MEMORY_CACHE.move_to_end(key)
            logger.info(f"[Cache] ⚡ L1 Memory Cache HIT (<0.5ms) for query: '{query[:40]}...'")
            return data
        else:
            del _L1_MEMORY_CACHE[key]

    # 2. Check L2 Redis Cache (~80ms)
    if redis_client:
        try:
            cached = redis_client.get(key)
            if cached:
                logger.info(f"[Cache] ⚡ L2 Redis Cache HIT (~80ms) for query: '{query[:40]}...'")
                data = json.loads(cached)
                # Promote to L1 Memory Cache
                _L1_MEMORY_CACHE[key] = (time.time(), data)
                if len(_L1_MEMORY_CACHE) > _MAX_L1_ITEMS:
                    _L1_MEMORY_CACHE.popitem(last=False)
                return data
        except Exception as e:
            logger.warning(f"[Cache] Redis get error: {e}")

    return None


def _async_save_l2_redis(key: str, data_json: str):
    """Worker function for async Redis writing."""
    if redis_client:
        try:
            redis_client.setex(key, CACHE_TTL, data_json)
        except Exception as e:
            logger.warning(f"[Cache] Async Redis write failed: {e}")


def set_cached_response(
    query: str,
    product_ids: List[str],
    response: Dict[str, Any],
    user_id: Optional[str] = None,
    doc_version: Optional[str] = None,
) -> None:
    """
    Save to L1 immediately, and dispatch L2 Redis save asynchronously (non-blocking).
    """
    key = get_cache_key(query, product_ids, user_id=user_id, doc_version=doc_version)

    # 1. Immediate write to L1 Memory Cache
    if len(_L1_MEMORY_CACHE) >= _MAX_L1_ITEMS:
        _L1_MEMORY_CACHE.popitem(last=False)
    _L1_MEMORY_CACHE[key] = (time.time(), response)

    # 2. Non-blocking asynchronous write to L2 Redis
    try:
        data_json = json.dumps(response, default=str)
        _cache_pool.submit(_async_save_l2_redis, key, data_json)
    except Exception as e:
        logger.debug(f"[Cache] Serialization error for cache write: {e}")


def clear_cache() -> None:
    """Clear L1 memory cache and L2 Redis cache (useful for test resets and document updates)."""
    _L1_MEMORY_CACHE.clear()
    if redis_client:
        try:
            keys = redis_client.keys("finex:query:*")
            if keys:
                redis_client.delete(*keys)
        except Exception as e:
            logger.warning(f"[Cache] Redis clear error: {e}")
