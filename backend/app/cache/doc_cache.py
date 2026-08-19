import json
from typing import Dict, Any, Optional
from app.cache.redis_client import redis_client

DOC_CACHE_TTL = 86400 * 3  # 3 days

def get_cached_document(doc_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve document metadata from Redis cache."""
    if not redis_client:
        return None
    try:
        data = redis_client.get(f"doc:{doc_id}")
        if data:
            return json.loads(data)
    except Exception:
        pass
    return None

def set_cached_document(doc_id: str, doc_data: Dict[str, Any]) -> None:
    """Store document metadata in Redis cache."""
    if not redis_client:
        return
    try:
        redis_client.setex(f"doc:{doc_id}", DOC_CACHE_TTL, json.dumps(doc_data))
    except Exception:
        pass
