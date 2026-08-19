from fastapi import Header, HTTPException, status, Depends
from supabase import Client
from app.db.supabase_client import get_supabase_client
from typing import Generator, Optional

def get_db() -> Client:
    """
    FastAPI dependency that yields the Supabase client instance.
    """
    return get_supabase_client()

def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Client = Depends(get_db)
) -> dict:
    """
    Validates Supabase JWT from Authorization header: 'Bearer <token>'
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ")[1]
    try:
        user_res = db.auth.get_user(token)
        if not user_res or not user_res.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token or user session expired",
            )
        return user_res.user.to_dict()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )
