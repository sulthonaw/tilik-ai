"""User settings and preference management service backed by HybridCache."""

import logging
from typing import Optional

from app.core.cache import cache
from app.models.schemas import UserRole

logger = logging.getLogger("user_service")

# 30 days TTL for user role preferences in cache/Redis
USER_ROLE_CACHE_TTL = 30 * 86400


class UserService:
    """Manages user preferences such as PEMULA vs EXPERT role."""

    @staticmethod
    def _role_key(google_id: str) -> str:
        return f"user_pref_role:{google_id}"

    def get_user_role(self, google_id: str) -> UserRole:
        """Retrieves stored user role preference, defaulting to PEMULA."""
        if not google_id:
            return UserRole.PEMULA

        cached_role = cache.get(self._role_key(google_id))
        if cached_role:
            try:
                # Handle string from redis or cached enum
                role_str = cached_role if isinstance(cached_role, str) else str(cached_role)
                return UserRole(role_str.upper())
            except (ValueError, KeyError):
                logger.warning(f"Invalid cached role '{cached_role}' for user {google_id}. Resetting to PEMULA.")

        return UserRole.PEMULA

    def set_user_role(self, google_id: str, role: UserRole) -> None:
        """Persists user role preference into Redis or in-memory cache."""
        if not google_id:
            return

        cache.set(self._role_key(google_id), role.value, ttl=USER_ROLE_CACHE_TTL)
        logger.info(f"User {google_id} role updated to {role.value}")


user_service = UserService()
