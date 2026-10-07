"""Multi-tier caching layer supporting Redis and In-Memory TTLCache for Sectors API credit optimization."""

import hashlib
import json
import logging
import threading
from typing import Any, Optional

from cachetools import TTLCache

from app.core.config import settings

logger = logging.getLogger("tilik_cache")


class HybridCache:
    """Thread-safe hybrid caching layer with Redis support and in-memory TTL fallback.

    Optimizes Sectors API credits by caching fundamental data per symbol/endpoint
    as well as full tweet verification responses.
    """

    def __init__(
        self,
        maxsize: int = settings.CACHE_MAXSIZE,
        default_ttl: int = settings.CACHE_TTL_SECONDS,
        redis_url: Optional[str] = settings.REDIS_URL,
        enable_redis: bool = settings.ENABLE_REDIS,
    ):
        self.default_ttl = default_ttl
        self._mem_cache = TTLCache(maxsize=maxsize, ttl=default_ttl)
        self._lock = threading.Lock()
        self._redis_client = None
        self.is_redis_active = False

        if enable_redis and redis_url:
            self._init_redis(redis_url)

    def _init_redis(self, redis_url: str) -> None:
        """Initializes Redis client with graceful failure handling."""
        try:
            import redis

            client = redis.Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=1.0,
                socket_timeout=1.0,
            )
            client.ping()
            self._redis_client = client
            self.is_redis_active = True
            logger.info(f"[Cache] Successfully connected to Redis at {redis_url}")
        except Exception as exc:
            self.is_redis_active = False
            self._redis_client = None
            logger.warning(
                f"[Cache] Redis unavailable ({type(exc).__name__}: {str(exc)[:100]}). "
                "Using In-Memory TTLCache fallback."
            )

    @staticmethod
    def hash_text(text: str) -> str:
        """Computes SHA256 hash of normalized text for verification response keys."""
        normalized = " ".join(text.strip().lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Retrieves an item from Redis or In-Memory cache."""
        if self.is_redis_active and self._redis_client is not None:
            try:
                raw_val = self._redis_client.get(key)
                if raw_val is not None:
                    return json.loads(raw_val)
                return None
            except Exception as e:
                logger.warning(f"[Cache Redis Error on GET {key}] {e}. Falling back to memory.")
                self.is_redis_active = False

        # In-Memory Cache Lookup
        with self._lock:
            return self._mem_cache.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Stores an item in Redis or In-Memory cache with specified TTL in seconds."""
        effective_ttl = ttl if ttl is not None else self.default_ttl

        if self.is_redis_active and self._redis_client is not None:
            try:
                # Handle Pydantic models, dicts, lists, primitives
                if hasattr(value, "model_dump_json"):
                    serialized = value.model_dump_json()
                elif hasattr(value, "dict"):
                    serialized = json.dumps(value.dict())
                else:
                    serialized = json.dumps(value)

                self._redis_client.setex(key, effective_ttl, serialized)
                return
            except Exception as e:
                logger.warning(f"[Cache Redis Error on SET {key}] {e}. Falling back to memory.")
                self.is_redis_active = False

        # In-Memory Cache Storage
        with self._lock:
            self._mem_cache[key] = value

    def delete(self, key: str) -> None:
        """Deletes a key from cache."""
        if self.is_redis_active and self._redis_client is not None:
            try:
                self._redis_client.delete(key)
            except Exception:
                pass

        with self._lock:
            if key in self._mem_cache:
                del self._mem_cache[key]

    def clear(self) -> None:
        """Clears all in-memory entries."""
        with self._lock:
            self._mem_cache.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._mem_cache)


# Global singleton instance
cache = HybridCache()
