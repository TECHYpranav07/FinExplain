import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App Info
    PROJECT_NAME: str = "FinExplain Backend"
    API_V1_STR: str = "/api/v1"

    # Supabase (PostgreSQL & Storage)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = os.getenv("SUPABASE_SERVICE_ROLE_KEY", None)

    # Pinecone (Vector Database)
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "fine-explain")

    # Groq (LLM Engine)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # Redis (Caching)
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Storage Bucket
    STORAGE_BUCKET: str = os.getenv("STORAGE_BUCKET")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()