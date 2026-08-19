import json
from typing import List, Optional
from app.cache.redis_client import redis_client
from app.utils.hash_utils import compute_md5
from app.ingestion.embedder import generate_embedding

EMBEDDING_CACHE_TTL = 86400 * 7  # 7 days

def get_cached_embedding(text: str) -> Optional[List[float]]:
    """Fetch cached embedding for text from Redis."""
    if not redis_client:
        return None
    key = f"emb:{compute_md5(text)}"
    try:
        data = redis_client.get(key)
        if data:
            return json.loads(data)
    except Exception:
        pass
    return None

def set_cached_embedding(text: str, embedding: List[float]) -> None:
    """Cache embedding in Redis."""
    if not redis_client:
        return
    key = f"emb:{compute_md5(text)}"
    try:
        redis_client.setex(key, EMBEDDING_CACHE_TTL, json.dumps(embedding))
    except Exception:
        pass

def get_or_create_embedding(text: str) -> List[float]:
    """Retrieve from cache if exists, otherwise generate and cache."""
    cached = get_cached_embedding(text)
    if cached is not None:
        return cached
    emb = generate_embedding(text)
    set_cached_embedding(text, emb)
    return emb
