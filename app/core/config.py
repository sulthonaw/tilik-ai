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
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Sectors API Settings
    SECTORS_API_KEY: Optional[str] = None
    SECTORS_API_BASE_URL: str = "https://api.sectors.app"

    # Slang RAG and Storage
    SLANG_CSV_PATH: str = str(ROOT_DIR / "data" / "slang_dictionary.csv")
    CHROMA_PERSIST_DIR: str = str(ROOT_DIR / "data" / "chroma_db")

    # Cache Settings
    CACHE_TTL_SECONDS: int = 3600
    CACHE_MAXSIZE: int = 1000

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    @property
    def effective_gemini_api_key(self) -> Optional[str]:
        """Returns GEMINI_API_KEY or GOOGLE_API_KEY if available."""
        return self.GEMINI_API_KEY or self.GOOGLE_API_KEY or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


@lru_cache()
def get_settings() -> Settings:
    """Returns a cached Settings singleton."""
    return Settings()


settings = get_settings()
