import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"

# Explicitly load .env from backend directory using dotenv
if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE, override=False)
else:
    load_dotenv(override=False)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App Info
    PROJECT_NAME: str = "FinExplain Backend"
    API_V1_STR: str = "/api/v1"

    # Environment: "development" or "production"
    # Controls whether demo fallbacks are allowed and whether critical keys are required.
    ENVIRONMENT: str = "development"

    # CORS allowed origins (comma-separated). Configured via CORS_ORIGINS in .env
    CORS_ORIGINS: str = ""

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse comma-separated CORS_ORIGINS from .env into a list of cleaned URLs."""
        raw = self.CORS_ORIGINS or os.getenv("CORS_ORIGINS", "")
        if not raw:
            return []
        return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]


    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    DATABASE_URL: Optional[str] = None

    # Pinecone
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "finexplain"

    # Google Gemini LLM Configuration
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    LLM_MODEL: Optional[str] = None

    # Redis (Caching)
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"

    # Hugging Face (Embeddings API)
    HUGGINGFACE_API_KEY: Optional[str] = None
    HF_TOKEN: Optional[str] = None
    HF_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Storage Bucket
    STORAGE_BUCKET: str = "loan_docs"

    # Authentication & JWT Configuration
    JWT_SECRET_KEY: str = "finexplain_super_secret_jwt_key_development_32chars_min"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    GOOGLE_CLIENT_ID: Optional[str] = None

    # Brevo Transactional Email Configuration
    BREVO_API_KEY: Optional[str] = None
    BREVO_FROM_EMAIL: str = "no-reply@finexplain.com"
    BREVO_FROM_NAME: str = "FinExplain Security"

    # Admin Credentials Configuration (.env)
    ADMIN_EMAIL: str = "admin@finexplain.com"
    ADMIN_PASSWORD: str = ""
    ADMIN_PS: Optional[str] = None

    @property
    def effective_admin_email(self) -> str:
        return (self.ADMIN_EMAIL or "admin@finexplain.com").lower().strip()

    @property
    def effective_admin_password(self) -> str:
        # Admin access must be explicitly configured; never ship a default password.
        return self.ADMIN_PS or self.ADMIN_PASSWORD or ""

    @property
    def effective_gemini_api_key(self) -> str:
        return self.GEMINI_API_KEY or self.GOOGLE_API_KEY or ""

    @property
    def active_llm_model(self) -> str:
        return self.GEMINI_MODEL or self.LLM_MODEL or "gemini-2.5-flash"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"

settings = Settings()

# Startup validation: fail-closed in non-dev mode if critical keys are missing
if not settings.is_development:
    _missing = []
    if not settings.SUPABASE_URL:
        _missing.append("SUPABASE_URL")
    if not settings.SUPABASE_KEY:
        _missing.append("SUPABASE_KEY")
    if not settings.effective_gemini_api_key:
        _missing.append("GEMINI_API_KEY (or GOOGLE_API_KEY)")
    if _missing:
        raise RuntimeError(
            f"ENVIRONMENT={settings.ENVIRONMENT} but critical settings are missing: "
            f"{', '.join(_missing)}. Set ENVIRONMENT=development for local dev mode."
        )
