from app.db.supabase_client import get_supabase_client
from typing import Optional, Dict, Any
import logging
import uuid

logger = logging.getLogger(__name__)


def ensure_user_exists(
    user_id: str,
    email: Optional[str] = None,
    full_name: Optional[str] = None,
    hashed_password: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Ensure the user ID exists in the Supabase public.users table.
    If the user does not exist, provisions it automatically to satisfy foreign key constraints.
    """
    supabase = get_supabase_client()
    if not supabase:
        return None

    try:
        # Check if user already exists
        res = supabase.table("users").select("id, email, full_name").eq("id", user_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]

        # User does not exist, insert new record
        safe_email = email or f"user_{user_id[:8]}@finexplain.local"
        safe_name = full_name or "Financial Auditor"
        safe_pwd = hashed_password or "oauth_or_authenticated"

        # Check if email is already taken by a different ID
        email_res = supabase.table("users").select("id").eq("email", safe_email).execute()
        if email_res.data and len(email_res.data) > 0:
            # Suffix email to guarantee uniqueness if ID differs
            safe_email = f"{safe_email.split('@')[0]}+{user_id[:6]}@{safe_email.split('@')[-1]}"

        insert_payload = {
            "id": user_id,
            "email": safe_email,
            "full_name": safe_name,
            "hashed_password": safe_pwd,
        }

        insert_res = supabase.table("users").insert(insert_payload).execute()
        if insert_res.data and len(insert_res.data) > 0:
            logger.info(f"Successfully provisioned user {user_id} in Supabase users table.")
            return insert_res.data[0]
        return None

    except Exception as e:
        logger.error(f"Error ensuring user {user_id} exists in Supabase: {e}")
        return None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve user from Supabase database by ID."""
    supabase = get_supabase_client()
    if not supabase:
        return None
    try:
        res = supabase.table("users").select("*").eq("id", user_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"Error retrieving user {user_id}: {e}")
        return None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieve user from Supabase database by email."""
    supabase = get_supabase_client()
    if not supabase:
        return None
    try:
        res = supabase.table("users").select("*").eq("email", email.lower().strip()).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"Error retrieving user by email {email}: {e}")
        return None


def create_user(
    user_id: str,
    email: str,
    full_name: str,
    hashed_password: str,
) -> Optional[Dict[str, Any]]:
    """Insert a new user record in Supabase users table."""
    supabase = get_supabase_client()
    if not supabase:
        return None
    try:
        payload = {
            "id": user_id,
            "email": email.lower().strip(),
            "full_name": full_name,
            "hashed_password": hashed_password,
        }
        res = supabase.table("users").insert(payload).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"Error creating user in Supabase: {e}")
        return None


def update_user_password(user_id: str, hashed_password: str) -> bool:
    """Update user password in Supabase."""
    supabase = get_supabase_client()
    if not supabase:
        return False
    try:
        supabase.table("users").update({"hashed_password": hashed_password}).eq("id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error updating password for user {user_id}: {e}")
        return False

