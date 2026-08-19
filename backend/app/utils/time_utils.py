from datetime import datetime, timezone

def get_utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)

def get_utc_now_iso() -> str:
    """Return ISO format string of current UTC datetime."""
    return get_utc_now().isoformat()
