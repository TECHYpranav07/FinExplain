from app.db.supabase_client import get_supabase_client
from typing import Optional, Dict, Any, List
from postgrest.types import CountMethod
import logging
import uuid

logger = logging.getLogger(__name__)

ADMIN_EMAILS = {"samadhanmane2324@gmail.com"}


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


# ---------------------------------------------------------------------------
# Admin helper functions
# ---------------------------------------------------------------------------

def get_user_role(user_id: str, email: Optional[str] = None) -> str:
    """Fetch the role for a user. Checks email first and falls back to Supabase query."""
    if email and email.lower().strip() in ADMIN_EMAILS:
        return "admin"

    supabase = get_supabase_client()
    if not supabase:
        return "user"
    try:
        res = supabase.table("users").select("id, email, role").eq("id", user_id).execute()
        if res.data and len(res.data) > 0:
            role = res.data[0].get("role")
            if role:
                return role
            user_email = res.data[0].get("email", "")
            if user_email.lower().strip() in ADMIN_EMAILS:
                return "admin"
        return "user"
    except Exception as e:
        logger.info(f"Role column query failed: {e}")
        try:
            res = supabase.table("users").select("id, email").eq("id", user_id).execute()
            if res.data and len(res.data) > 0:
                user_email = res.data[0].get("email", "")
                if user_email.lower().strip() in ADMIN_EMAILS:
                    return "admin"
        except Exception:
            pass
        return "user"


def update_user_role(user_id: str, role: str) -> bool:
    """Update a user's role in Supabase."""
    supabase = get_supabase_client()
    if not supabase:
        return False
    try:
        supabase.table("users").update({"role": role}).eq("id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error updating role for user {user_id}: {e}")
        return False


def get_all_users(limit: int = 50, offset: int = 0, search: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch all users with optional search and pagination."""
    supabase = get_supabase_client()
    if not supabase:
        return []
    try:
        query = supabase.table("users").select("id, email, full_name, created_at, updated_at")
        try:
            query = supabase.table("users").select("id, email, full_name, role, created_at, updated_at")
        except Exception:
            pass

        if search:
            query = query.or_(f"email.ilike.%{search}%,full_name.ilike.%{search}%")

        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        res = query.execute()
        users = res.data or []

        for u in users:
            if not u.get("role"):
                email = u.get("email", "").lower().strip()
                u["role"] = "admin" if email in ADMIN_EMAILS else "user"

        return users
    except Exception as e:
        logger.error(f"Error fetching all users: {e}")
        try:
            query = supabase.table("users").select("id, email, full_name, created_at, updated_at")
            if search:
                query = query.or_(f"email.ilike.%{search}%,full_name.ilike.%{search}%")
            query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
            res = query.execute()
            users = res.data or []
            for u in users:
                email = u.get("email", "").lower().strip()
                u["role"] = "admin" if email in ADMIN_EMAILS else "user"
            return users
        except Exception as e2:
            logger.error(f"Error fetching users (fallback): {e2}")
            return []


def count_all_users() -> int:
    """Count total users in the database."""
    supabase = get_supabase_client()
    if not supabase:
        return 0
    try:
        res = supabase.table("users").select("id", count=CountMethod.exact).execute()
        return res.count if hasattr(res, "count") and res.count is not None else len(res.data or [])
    except Exception as e:
        logger.error(f"Error counting users: {e}")
        return 0


def delete_user(user_id: str) -> bool:
    """Delete a user from the database."""
    supabase = get_supabase_client()
    if not supabase:
        return False
    try:
        supabase.table("users").delete().eq("id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return False
