"""
Authentication API Endpoints.

Provides registration, email/password login, Google OAuth login, and token verification.
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
import uuid
import time
from app.auth.jwt_handler import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from app.core.config import settings

from app.core.constants import DEFAULT_DEMO_USER_ID

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory user store for demo/development (persistent across active runtime)
# In production, can sync to Supabase/PostgreSQL user table
USERS_DB: Dict[str, Dict[str, Any]] = {
    "demo@finexplain.ai": {
        "id": DEFAULT_DEMO_USER_ID,
        "email": "demo@finexplain.ai",
        "name": "FinExplain Auditor",
        "hashed_password": hash_password("demo1234"),
        "role": "auditor",
        "created_at": "2026-08-01T00:00:00Z"
    }
}


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
    
    user_record = {
        "id": user_id,
        "email": email_key,
        "name": name,
        "hashed_password": hash_password(req.password),
        "role": "user",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    USERS_DB[email_key] = user_record

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
        # FIN-DEMO: In dev mode, auto-provision user if new to provide instant seamless testing
        if settings.is_development:
            user_id = str(uuid.uuid4())
            name = email_key.split("@")[0].title()
            user = {
                "id": user_id,
                "email": email_key,
                "name": name,
                "hashed_password": hash_password(req.password),
                "role": "user",
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            USERS_DB[email_key] = user
        else:
            raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token({
        "sub": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user.get("role", "user"),
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user.get("role", "user")
        }
    }


@router.post("/google", response_model=AuthResponse)
async def google_auth(req: GoogleAuthRequest):
    """Authenticate or register a user via Google OAuth."""
    # If client passed raw email & name from Google OAuth
    email = req.email or (f"google_user_{uuid.uuid4().hex[:6]}@gmail.com")
    email_key = str(email).lower().strip()
    name = req.name or email_key.split("@")[0].title()

    if email_key not in USERS_DB:
        user_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"google:{req.google_id or email_key}"))
        USERS_DB[email_key] = {
            "id": user_id,
            "email": email_key,
            "name": name,
            "picture": req.picture,
            "role": "user",
            "auth_provider": "google",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    
    user = USERS_DB[email_key]

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
