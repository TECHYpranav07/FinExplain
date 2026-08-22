# FIN-041: security.py — Safe stub
#
# The original security.py contained a hardcoded JWT secret, unsalted SHA-256
# password hashing, and a dummy token fallback. All authentication in FinExplain
# should use Supabase Auth via app.api.dependencies.get_current_user().
#
# This file is intentionally emptied of cryptographic operations to prevent
# accidental use of the unsafe implementations. If custom JWT/password logic
# is needed in the future, use a proper library (e.g., passlib with bcrypt/argon2)
# and load the secret from environment variables.


def _not_implemented():
    """Guard against accidental use of removed security helpers."""
    raise NotImplementedError(
        "Custom JWT/password helpers have been removed (FIN-041). "
        "Use Supabase Auth via app.api.dependencies.get_current_user() instead."
    )


def hash_password(password: str) -> str:
    _not_implemented()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    _not_implemented()


def create_access_token(data: dict, expires_delta=None) -> str:
    _not_implemented()


def decode_access_token(token: str) -> dict:
    _not_implemented()
