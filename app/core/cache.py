"""In-memory SHA256 caching layer for verification results."""

import hashlib
import threading
from typing import Any, Optional

from cachetools import TTLCache

from app.core.config import settings


class VerificationCache:
    """Thread-safe TTL in-memory cache keyed by SHA256 of normalized text."""

    def __init__(self, maxsize: int = settings.CACHE_MAXSIZE, ttl: int = settings.CACHE_TTL_SECONDS):
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = threading.Lock()

    @staticmethod
    def hash_text(text: str) -> str:
        """Computes SHA256 hash of normalized text."""
        normalized = " ".join(text.strip().lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def get(self, text: str) -> Optional[Any]:
        """Retrieves cached item if present."""
        key = self.hash_text(text)
        with self._lock:
            return self._cache.get(key)

    def set(self, text: str, value: Any) -> None:
        """Stores item in cache."""
        key = self.hash_text(text)
        with self._lock:
            self._cache[key] = value

    def clear(self) -> None:
        """Clears all cached entries."""
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)


# Global singleton instance
cache = VerificationCache()
