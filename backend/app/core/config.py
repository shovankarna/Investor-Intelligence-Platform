import json
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General App Config
    APP_NAME: str = "Investor Intelligence Platform"
    APP_ENV: str = Field(default="development", description="Runtime environment")
    PORT: int = Field(default=8000, description="Backend server port")
    ALLOWED_ORIGINS: list[str] | str = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origin domains",
    )

    @field_validator("ALLOWED_ORIGINS", mode="after")
    @classmethod
    def parse_allowed_origins(cls, v: list[str] | str) -> list[str]:
        """Support JSON string, comma-separated string, or Python list for CORS origins."""
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # OpenRouter API & Resiliency
    OPENROUTER_API_KEY: str = Field(
        default="",
        description="OpenRouter API key for LLM inference",
    )
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_DEFAULT_MODEL: str = "google/gemma-4-26b-a4b-it:free"
    OPENROUTER_FALLBACK_MODELS: list[str] = [
        "nvidia/nemotron-3-super-120b-a12b:free",
        "openrouter/free",
        "google/gemma-4-31b-it:free",
    ]

    # Langfuse LLM Observability & Monitoring (Free Tier)
    LANGFUSE_PUBLIC_KEY: str = Field(default="", description="Langfuse public API key")
    LANGFUSE_SECRET_KEY: str = Field(default="", description="Langfuse secret API key")
    LANGFUSE_HOST: str = Field(
        default="https://us.cloud.langfuse.com",
        description="Langfuse host URL (e.g. https://cloud.langfuse.com or https://us.cloud.langfuse.com)",
    )
    LANGFUSE_BASE_URL: str | None = Field(default=None, description="Alias for LANGFUSE_HOST")

    # Database Configuration (Postgres + pgvector)
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/postgres",
        description="Async database connection string",
    )
    DATABASE_URL_SYNC: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/postgres",
        description="Sync database connection string for migrations",
    )

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def normalize_async_db_url(cls, v: str) -> str:
        """Ensure async database URL uses postgresql+asyncpg:// driver."""
        if v.startswith("postgres://"):
            return "postgresql+asyncpg://" + v[len("postgres://") :]
        if v.startswith("postgresql://"):
            return "postgresql+asyncpg://" + v[len("postgresql://") :]
        return v

    @field_validator("DATABASE_URL_SYNC", mode="after")
    @classmethod
    def normalize_sync_db_url(cls, v: str) -> str:
        """Ensure sync database URL uses postgresql:// driver for migrations."""
        if v.startswith("postgresql+asyncpg://"):
            return "postgresql://" + v[len("postgresql+asyncpg://") :]
        if v.startswith("postgres://"):
            return "postgresql://" + v[len("postgres://") :]
        return v

    # Supabase Cloud & Storage (Supports Modern Publishable/Secret Keys & Legacy Keys)
    SUPABASE_URL: str = Field(default="", description="Supabase project URL")
    SUPABASE_PUBLISHABLE_KEY: str = Field(
        default="", description="Modern Supabase Publishable Key (replaces anon key)"
    )
    SUPABASE_SECRET_KEY: str = Field(
        default="", description="Modern Supabase Secret Key (replaces service_role key)"
    )
    SUPABASE_ANON_KEY: str = Field(
        default="", description="Legacy Supabase anon public key"
    )
    SUPABASE_SERVICE_ROLE_KEY: str = Field(
        default="", description="Legacy Supabase service role private key"
    )
    SUPABASE_BUCKET_NAME: str = "filings"

    @property
    def effective_supabase_publishable_key(self) -> str:
        """Returns modern publishable key or fallback to legacy anon key."""
        return self.SUPABASE_PUBLISHABLE_KEY or self.SUPABASE_ANON_KEY

    @property
    def effective_supabase_secret_key(self) -> str:
        """Returns modern secret key or fallback to legacy service role key."""
        return self.SUPABASE_SECRET_KEY or self.SUPABASE_SERVICE_ROLE_KEY

    # ML & RAG In-Process Model Defaults (PROJECT.md §12)
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"
    RERANKER_MODEL_NAME: str = "BAAI/bge-reranker-base"
    EMBEDDING_DIMENSION: int = 384
    CHUNK_MIN_TOKENS: int = 300
    CHUNK_MAX_TOKENS: int = 600
    CHUNK_OVERLAP_PERCENTAGE: float = 0.10
    RETRIEVAL_TOP_K: int = 20
    RERANKER_TOP_N: int = 5


settings = Settings()

# Propagate Langfuse credentials to os.environ so @observe auto-initializes
import os

if settings.LANGFUSE_PUBLIC_KEY:
    os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY
if settings.LANGFUSE_SECRET_KEY:
    os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY
_lf_host = settings.LANGFUSE_BASE_URL or settings.LANGFUSE_HOST
if _lf_host:
    os.environ["LANGFUSE_HOST"] = _lf_host
    os.environ["LANGFUSE_BASE_URL"] = _lf_host
