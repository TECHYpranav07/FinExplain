import hashlib
import json
import logging
from typing import List, Dict, Any, Optional
from app.cache.redis_client import redis_client
from app.core.constants import DEFAULT_GROQ_MODEL

logger = logging.getLogger(__name__)

CACHE_TTL = 3600  # FIN-032: 1 hour in seconds (reduced from 24h)
PIPELINE_VERSION = "v2"

def get_cache_key(query: str, product_ids: List[str]) -> str:
    """Generate a deterministic versioned cache key based on query, product IDs, and model."""
    product_str = "_".join(sorted(str(p) for p in product_ids))
    unique_string = f"{PIPELINE_VERSION}:{DEFAULT_GROQ_MODEL}:{query.strip().lower()}:{product_str}"
    return f"query:{hashlib.sha256(unique_string.encode()).hexdigest()}"

def get_cached_response(query: str, product_ids: List[str]) -> Optional[Dict[str, Any]]:
    """Retrieve cached response if available."""
    if not redis_client:
        return None
    
    key = get_cache_key(query, product_ids)
    try:
        cached = redis_client.get(key)
        if cached:
            logger.info(f"✅ Cache hit for query: {query[:50]}...")
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Cache get error: {e}")
    return None

def set_cached_response(query: str, product_ids: List[str], response: Dict[str, Any]) -> None:
    """Store the response in cache."""
    if not redis_client:
        return
    
    key = get_cache_key(query, product_ids)
    try:
        redis_client.setex(key, CACHE_TTL, json.dumps(response, default=str))
        logger.info(f"✅ Cached response for query: {query[:50]}...")
    except Exception as e:
        logger.warning(f"Cache set error: {e}")