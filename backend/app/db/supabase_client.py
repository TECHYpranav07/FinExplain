from supabase import create_client, Client
from app.core.config import settings

_supabase_client: Client = None

def get_supabase_client() -> Client:
    """
    Singleton Supabase client instance.
    Uses the Service Role Key for full access (bypasses RLS).
    """
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )
    return _supabase_client