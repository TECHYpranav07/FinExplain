import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.jwt_handler import create_access_token
from app.core.security_middleware import SlidingWindowRateLimiter

client = TestClient(app)


def test_sliding_window_rate_limiter_exceed():
    limiter = SlidingWindowRateLimiter()
    key = "test_client_ip"
    max_req = 5

    for i in range(max_req):
        is_limited, remaining, retry_after = limiter.is_rate_limited(key, max_requests=max_req, window_seconds=60)
        assert not is_limited
        assert remaining == max_req - 1 - i

    # Next request should be blocked
    is_limited, remaining, retry_after = limiter.is_rate_limited(key, max_requests=max_req, window_seconds=60)
    assert is_limited
    assert remaining == 0
    assert retry_after > 0


def test_unauthenticated_api_request_rejected_with_401():
    """Unauthenticated direct API calls must receive 401 Unauthorized."""
    response = client.get("/api/v1/products/")
    assert response.status_code == 401
    assert "Authentication required" in response.json().get("detail", "")


def test_authenticated_api_request_with_jwt_succeeds():
    """Authenticated request with valid JWT token succeeds or passes security gate."""
    token = create_access_token({
        "sub": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        "email": "auditor@finexplain.ai",
        "name": "Auditor"
    })
    response = client.get(
        "/api/v1/products/",
        headers={"Authorization": f"Bearer {token}"}
    )
    # Status code should not be 401 Unauthorized
    assert response.status_code in (200, 404)


def test_security_headers_present():
    """Verify standard OWASP security headers on responses."""
    response = client.get("/health/live")
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("x-xss-protection") == "1; mode=block"
    assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
