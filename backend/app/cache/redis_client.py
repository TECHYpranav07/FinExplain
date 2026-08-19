import redis
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Try to connect to Redis; if it fails, we'll set a dummy client
redis_client = None

try:
    if settings.REDIS_URL:
        redis_client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2
        )
        # Test connection
        redis_client.ping()
        logger.info("✅ Connected to Redis successfully")
    else:
        logger.warning("⚠️ REDIS_URL not set, caching disabled")
except Exception as e:
    logger.warning(f"⚠️ Redis connection failed: {e}. Caching disabled.")
    redis_client = None