from supabase import create_client, Client
from app.core.config import settings

_supabase_client: Client = None

def get_supabase_client() -> Client:
    """
    Singleton Supabase client instance.
    Uses SUPABASE_URL and SUPABASE_KEY.
    """
    global _supabase_client
    if _supabase_client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be configured in environment variables.")
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )
    return _supabase_client