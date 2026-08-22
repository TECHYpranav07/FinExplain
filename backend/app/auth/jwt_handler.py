"""
JWT and Authentication Token Handler.

Provides password hashing, verification, JWT token creation, and Google ID token validation.
"""

import time
import json
import base64
import hmac
import hashlib
from typing import Optional, Dict, Any
from app.core.config import settings

try:
    import jwt
    HAS_PYJWT = True
except ImportError:
    HAS_PYJWT = False


def hash_password(password: str) -> str:
    """Hash a password securely using PBKDF2-HMAC-SHA256 with salt."""
    salt = "finexplain_salt_2026"
    pwd_bytes = password.encode("utf-8")
    salt_bytes = salt.encode("utf-8")
    hashed = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt_bytes, iterations=100_000)
    return hashed.hex()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hashed hex."""
    return hash_password(plain_password) == hashed_password


def create_access_token(data: Dict[str, Any], expires_delta_minutes: Optional[int] = None) -> str:
    """Generate a signed JWT access token."""
    expire_minutes = expires_delta_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    expire_time = int(time.time()) + (expire_minutes * 60)
    
    payload = data.copy()
    payload.update({
        "exp": expire_time,
        "iat": int(time.time()),
        "iss": "finexplain",
    })

    if HAS_PYJWT:
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    else:
        # Pure Python HMAC-SHA256 fallback
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        signature = hmac.new(
            settings.JWT_SECRET_KEY.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256
        ).digest()
        sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
        return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token."""
    try:
        if HAS_PYJWT:
            return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        else:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header_b64, payload_b64, sig_b64 = parts
            
            # Verify signature
            rem = len(sig_b64) % 4
            if rem:
                sig_b64 += "=" * (4 - rem)
            expected_sig = hmac.new(
                settings.JWT_SECRET_KEY.encode(),
                f"{header_b64}.{payload_b64}".encode(),
                hashlib.sha256
            ).digest()
            actual_sig = base64.urlsafe_b64decode(sig_b64)
            if not hmac.compare_digest(expected_sig, actual_sig):
                return None
            
            # Decode payload
            rem_p = len(payload_b64) % 4
            if rem_p:
                payload_b64 += "=" * (4 - rem_p)
            payload_json = base64.urlsafe_b64decode(payload_b64).decode()
            payload = json.loads(payload_json)
            
            # Check expiration
            if "exp" in payload and payload["exp"] < int(time.time()):
                return None
            return payload
    except Exception:
        return None
