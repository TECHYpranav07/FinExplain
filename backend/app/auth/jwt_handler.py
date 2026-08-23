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


import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.constants import DEFAULT_DEMO_USER_ID

security = HTTPBearer(auto_error=False)


def ensure_valid_uuid(val: Any) -> str:
    """Ensure a user ID string is a valid RFC 4122 UUID for PostgreSQL compatibility."""
    if not val:
        return DEFAULT_DEMO_USER_ID
    val_str = str(val).strip()
    try:
        return str(uuid.UUID(val_str))
    except (ValueError, AttributeError, TypeError):
        # Deterministically convert arbitrary string into a valid UUIDv5
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, val_str))


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """
    Extract and validate authenticated user from Bearer JWT token.
    Strictly enforces authorization: unauthenticated requests receive 401 Unauthorized.
    """
    if credentials and credentials.credentials:
        token = credentials.credentials
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            raw_id = payload["sub"]
            valid_uuid = ensure_valid_uuid(raw_id)
            return {
                "id": valid_uuid,
                "email": payload.get("email", ""),
                "name": payload.get("name", ""),
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please provide a valid Authorization Bearer token.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[Dict[str, Any]]:
    """Optional user extractor for public endpoints."""
    if credentials and credentials.credentials:
        token = credentials.credentials
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            raw_id = payload["sub"]
            return {
                "id": ensure_valid_uuid(raw_id),
                "email": payload.get("email", ""),
                "name": payload.get("name", ""),
            }
    return None


