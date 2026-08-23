"""
Security & Rate Limiting Middleware.

Provides:
1. In-memory sliding-window Rate Limiting per IP / Token to protect against DDoS,
   brute-force login attempts, and LLM query flooding.
2. Standard HTTP Security Headers (OWASP recommendations).
3. Request Payload Size Guard to prevent memory exhaustion attacks.
"""

import time
import logging
from collections import defaultdict
from typing import Dict, List, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

logger = logging.getLogger(__name__)


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter tracking request timestamps per client identifier.
    """

    def __init__(self):
        # Maps client_key -> List of epoch timestamps
        self._records: Dict[str, List[float]] = defaultdict(list)
        # Cleanup threshold
        self._last_cleanup = time.time()

    def is_rate_limited(self, client_key: str, max_requests: int, window_seconds: int = 60) -> Tuple[bool, int, int]:
        """
        Check if client_key has exceeded max_requests in the last window_seconds.
        Returns: (is_limited, remaining_requests, retry_after_seconds)
        """
        now = time.time()
        window_start = now - window_seconds

        # Periodic cleanup of stale records every 5 minutes
        if now - self._last_cleanup > 300:
            self._cleanup(window_start)
            self._last_cleanup = now

        timestamps = self._records[client_key]
        # Keep only timestamps within the current sliding window
        valid_timestamps = [ts for ts in timestamps if ts > window_start]
        self._records[client_key] = valid_timestamps

        current_count = len(valid_timestamps)
        if current_count >= max_requests:
            # Oldest timestamp in window dictates when a slot opens up
            oldest_ts = valid_timestamps[0]
            retry_after = max(1, int(oldest_ts + window_seconds - now))
            return True, 0, retry_after

        # Record this request
        valid_timestamps.append(now)
        remaining = max_requests - len(valid_timestamps)
        return False, remaining, 0

    def _cleanup(self, cutoff: float):
        keys_to_delete = []
        for key, timestamps in self._records.items():
            self._records[key] = [ts for ts in timestamps if ts > cutoff]
            if not self._records[key]:
                keys_to_delete.append(key)
        for key in keys_to_delete:
            del self._records[key]


# Global rate limiter instance
_rate_limiter = SlidingWindowRateLimiter()


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    High-performance middleware handling DDoS rate limiting, payload protection,
    and HTTP security headers.
    """

    # Maximum payload size in bytes (30 MB for document upload support)
    MAX_CONTENT_LENGTH = 30 * 1024 * 1024

    # Route-specific rate limits (requests per 60-second window)
    RATE_LIMITS = {
        "/api/v1/auth": 20,       # 20 req/min for auth endpoints (prevents brute-force)
        "/api/v1/queries": 40,    # 40 req/min for AI queries (protects LLM compute & cost)
        "/api/v1/analysis": 40,   # 40 req/min for document analysis
        "/api/v1/admin": 30,      # 30 req/min for admin panel endpoints
        "default": 120,           # 120 req/min for general API endpoints
    }

    async def dispatch(self, request: Request, call_next):
        # 1. Payload Size Check
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.MAX_CONTENT_LENGTH:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request payload exceeds maximum allowed size (30MB)."}
                    )
            except ValueError:
                pass

        # 2. Extract Client Key (IP address + Authorization Token if present)
        client_ip = request.client.host if request.client else "unknown_ip"
        auth_header = request.headers.get("authorization", "")
        client_key = f"{client_ip}:{auth_header[:25]}" if auth_header else client_ip

        # 3. Determine Rate Limit based on route
        path = request.url.path
        limit = self.RATE_LIMITS["default"]
        for prefix, prefix_limit in self.RATE_LIMITS.items():
            if prefix != "default" and path.startswith(prefix):
                limit = prefix_limit
                break

        # Public static assets and health check bypass rate limiting
        if not path.startswith("/health") and not path.startswith("/assets") and path != "/":
            is_limited, remaining, retry_after = _rate_limiter.is_rate_limited(
                client_key=f"{client_key}:{path[:20]}",
                max_requests=limit,
                window_seconds=60
            )

            if is_limited:
                logger.warning(f"Rate limit exceeded for client {client_ip} on {path}. Retry after {retry_after}s.")
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": f"Rate limit exceeded. Too many requests on '{path}'. Please retry in {retry_after} seconds.",
                        "retry_after_seconds": retry_after
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0"
                    }
                )

        # 4. Process Request
        response: Response = await call_next(request)

        # 5. Inject OWASP Standard Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
