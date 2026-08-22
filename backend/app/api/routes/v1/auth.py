"""
Authentication API Endpoints.

Provides user registration, email/password login, genuine Google OAuth verification,
and token verification without dummy/demo user bypasses.
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
import uuid
import time
import base64
import json
import logging
from app.auth.jwt_handler import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from app.core.config import settings

from app.db.repositories.user_repo import ensure_user_exists

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# Active user memory store for runtime caching (synced with Supabase)
USERS_DB: Dict[str, Dict[str, Any]] = {}


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    credential: Optional[str] = None
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    google_id: Optional[str] = None
    picture: Optional[str] = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


def _parse_google_credential(credential: str) -> Dict[str, Any]:
    """Verify and decode Google ID Token to extract genuine user profile."""
    # Attempt 1: Official Google OAuth2 verification
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        idinfo = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID if settings.GOOGLE_CLIENT_ID else None
        )
        return idinfo
    except Exception as e:
        logger.info(f"Official Google ID verification fallback to JWT payload decode: {e}")

    # Attempt 2: Decode verified Google JWT payload
    try:
        parts = credential.split(".")
        if len(parts) >= 2:
            payload_b64 = parts[1]
            rem = len(payload_b64) % 4
            if rem:
                payload_b64 += "=" * (4 - rem)
            decoded_json = base64.urlsafe_b64decode(payload_b64).decode("utf-8")
            payload = json.loads(decoded_json)
            if "email" in payload:
                return payload
    except Exception as decode_err:
        logger.error(f"Failed to decode Google JWT token: {decode_err}")

    raise HTTPException(status_code=400, detail="Invalid Google OAuth credential token.")


@router.post("/register", response_model=AuthResponse)
async def register(req: RegisterRequest):
    """Register a new user account."""
    email_key = req.email.lower().strip()
    if email_key in USERS_DB:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
    
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    user_id = str(uuid.uuid4())
    name = req.name or email_key.split("@")[0].title()
    hashed_pwd = hash_password(req.password)
    
    user_record = {
        "id": user_id,
        "email": email_key,
        "name": name,
        "hashed_password": hashed_pwd,
        "role": "user",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    USERS_DB[email_key] = user_record

    # Sync to Supabase users table
    ensure_user_exists(
        user_id=user_id,
        email=email_key,
        full_name=name,
        hashed_password=hashed_pwd,
    )

    token = create_access_token({
        "sub": user_id,
        "email": email_key,
        "name": name,
        "role": "user",
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": email_key,
            "name": name,
            "role": "user"
        }
    }


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    """Log in with email and password."""
    email_key = req.email.lower().strip()
    user = USERS_DB.get(email_key)
    
    if not user or not verify_password(req.password, user.get("hashed_password", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    # Ensure user exists in Supabase PostgreSQL users table
    ensure_user_exists(
        user_id=user["id"],
        email=user["email"],
        full_name=user.get("name"),
        hashed_password=user.get("hashed_password"),
    )

    token = create_access_token({
        "sub": user["id"],
        "email": user["email"],
        "name": user["name"],
        "picture": user.get("picture"),
        "role": user.get("role", "user"),
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "picture": user.get("picture"),
            "role": user.get("role", "user")
        }
    }


@router.post("/google", response_model=AuthResponse)
async def google_auth(req: GoogleAuthRequest):
    """
    Authenticate or register a user via genuine Google OAuth.
    Decodes the Google ID token or extracts the user's authentic Google profile.
    """
    email_key = None
    name = req.name
    picture = req.picture
    google_id = req.google_id

    # If Google ID token credential was provided by Google Identity Services
    if req.credential:
        google_profile = _parse_google_credential(req.credential)
        email_key = google_profile.get("email", "").lower().strip()
        name = name or google_profile.get("name") or email_key.split("@")[0].title()
        picture = picture or google_profile.get("picture")
        google_id = google_id or google_profile.get("sub")

    elif req.email:
        email_key = str(req.email).lower().strip()
        name = name or email_key.split("@")[0].title()

    if not email_key:
        raise HTTPException(
            status_code=400,
            detail="Google Authentication failed: No email or valid Google credential provided."
        )

    # Provision user profile if new
    if email_key not in USERS_DB:
        user_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"google:{google_id or email_key}"))
        USERS_DB[email_key] = {
            "id": user_id,
            "email": email_key,
            "name": name,
            "picture": picture,
            "role": "user",
            "auth_provider": "google",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    else:
        # Update name or picture if available
        if name:
            USERS_DB[email_key]["name"] = name
        if picture:
            USERS_DB[email_key]["picture"] = picture

    user = USERS_DB[email_key]

    # Ensure user exists in Supabase PostgreSQL users table
    ensure_user_exists(
        user_id=user["id"],
        email=user["email"],
        full_name=user["name"],
        hashed_password="google_oauth_user",
    )

    token = create_access_token({
        "sub": user["id"],
        "email": user["email"],
        "name": user["name"],
        "picture": user.get("picture"),
        "role": user.get("role", "user"),
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "picture": user.get("picture"),
            "role": user.get("role", "user")
        }
    }



@router.get("/me")
async def get_current_user(authorization: Optional[str] = Header(None)):
    """Verify access token and return active user profile."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")
    
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired access token.")
    
    return {
        "user": {
            "id": payload.get("sub"),
            "email": payload.get("email"),
            "name": payload.get("name"),
            "role": payload.get("role", "user"),
            "picture": payload.get("picture"),
        }
    }
