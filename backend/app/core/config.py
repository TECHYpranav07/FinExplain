from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"

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

    # CORS allowed origins (comma-separated). FIN-004: no more wildcard.
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8000"

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
    GEMINI_MODEL: str = "gemini-2.5-flash"
    LLM_MODEL: Optional[str] = None

    # Redis (Caching)
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"

    # Hugging Face (Embeddings API)
    HUGGINGFACE_API_KEY: Optional[str] = None
    HF_TOKEN: Optional[str] = None
    HF_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Storage Bucket
    STORAGE_BUCKET: str = "loan_docs"

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
