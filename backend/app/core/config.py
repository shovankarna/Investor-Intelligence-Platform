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
    OPENROUTER_DEFAULT_MODEL: str = "deepseek/deepseek-v4-flash:free"
    OPENROUTER_FALLBACK_MODELS: list[str] = [
        "moonshotai/kimi-k2.6:free",
        "nex-agi/nex-n2-pro:free",
        "openrouter/free",
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

    # Supabase Cloud & Storage
    SUPABASE_URL: str = Field(default="", description="Supabase project URL")
    SUPABASE_ANON_KEY: str = Field(default="", description="Supabase anon public key")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(
        default="", description="Supabase service role private key"
    )
    SUPABASE_BUCKET_NAME: str = "filings"

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
