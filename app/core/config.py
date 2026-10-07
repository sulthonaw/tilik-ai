"""Application configuration settings using pydantic-settings."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Global configuration settings for Tilik AI."""

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Tilik AI Backend"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    VERSION: str = "2.0.0"

    # Google Gemini Settings
    GOOGLE_API_KEY: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"
    GEMINI_FALLBACK_MODELS: list[str] = ["gemini-3.1-flash-lite-preview", "gemini-2.5-flash"]

    # Sectors API Settings
    SECTORS_API_KEY: Optional[str] = None
    SECTORS_API_BASE_URL: str = "https://api.sectors.app"

    # Slang RAG and Storage
    SLANG_CSV_PATH: str = str(ROOT_DIR / "data" / "slang_dictionary.csv")
    CHROMA_PERSIST_DIR: str = str(ROOT_DIR / "data" / "chroma_db")

    # Cache & Redis Settings
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"
    ENABLE_REDIS: bool = True
    CACHE_TTL_SECONDS: int = 3600
    CACHE_MAXSIZE: int = 2000

    # Sectors Fundamental API Cache TTLs (Credit Optimization)
    CACHE_TTL_COMPANY_REPORT: int = 86400       # 24 jam (4 credits)
    CACHE_TTL_QUARTERLY_FINANCIALS: int = 86400  # 24 jam (4 credits)
    CACHE_TTL_BROKER_SUMMARY: int = 1800         # 30 menit (2 credits)
    CACHE_TTL_FOREIGN_FLOW: int = 1800           # 30 menit (1 credit)
    CACHE_TTL_SUSPENSIONS: int = 7200            # 2 jam (1 credit)

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Google OAuth & JWT Authentication
    GOOGLE_CLIENT_ID: Optional[str] = None
    JWT_SECRET_KEY: str = "tilik-ai-dev-secret-key-change-in-production-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 jam

    @property
    def effective_gemini_api_key(self) -> Optional[str]:
        """Returns GEMINI_API_KEY or GOOGLE_API_KEY if available."""
        return self.GEMINI_API_KEY or self.GOOGLE_API_KEY or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


@lru_cache()
def get_settings() -> Settings:
    """Returns a cached Settings singleton."""
    return Settings()


settings = get_settings()
