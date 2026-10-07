"""Security, rate limiting, and request sanitization utilities."""

import re
import time
from collections import defaultdict
from typing import Dict, List, Tuple

from fastapi import HTTPException, Request, status

from app.core.config import settings


class RateLimiter:
    """Simple in-memory sliding window rate limiter."""

    def __init__(self, limit_per_minute: int = settings.RATE_LIMIT_PER_MINUTE):
        self.limit = limit_per_minute
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> Tuple[bool, int]:
        """Checks if client request is within rate limits.

        Returns (allowed, retry_after_seconds).
        """
        now = time.time()
        window_start = now - 60.0
        # Filter out timestamps older than 1 minute
        valid_timestamps = [t for t in self.requests[client_id] if t > window_start]
        self.requests[client_id] = valid_timestamps

        if len(valid_timestamps) >= self.limit:
            oldest = valid_timestamps[0]
            retry_after = max(1, int(60.0 - (now - oldest)))
            return False, retry_after

        self.requests[client_id].append(now)
        return True, 0


rate_limiter = RateLimiter()


def sanitize_input_text(text: str) -> str:
    """Sanitizes raw social media text, stripping control characters and excessive whitespace."""
    if not text:
        return ""
    # Remove control characters except standard line breaks
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Normalize multiple whitespace characters
    cleaned = re.sub(r"[ \t]+", " ", cleaned).strip()
    return cleaned


async def check_rate_limit(request: Request) -> None:
    """FastAPI dependency to enforce per-IP rate limiting."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    allowed, retry_after = rate_limiter.is_allowed(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )


# ==========================================
# GOOGLE OAUTH & JWT UTILITIES
# ==========================================
from datetime import datetime, timedelta, timezone
import logging
from typing import Optional
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
import jwt

from app.models.schemas import UserPayload

logger = logging.getLogger("security")

security_bearer_optional = HTTPBearer(auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a signed JWT access token for Tilik AI."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Decodes and validates a Tilik AI JWT access token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except Exception as e:
        logger.debug(f"JWT decode error: {e}")
        return None


def verify_google_id_token(token_str: str) -> dict:
    """Verifies a Google ID Token using official google-auth library.
    
    Raises ValueError if token is invalid or expired.
    """
    try:
        audience = settings.GOOGLE_CLIENT_ID if settings.GOOGLE_CLIENT_ID else None
        id_info = google_id_token.verify_oauth2_token(
            token_str,
            google_requests.Request(),
            audience=audience,
        )
        return id_info
    except Exception as e:
        logger.warning(f"Google ID token verification failed: {e}")
        raise ValueError(f"Token Google tidak valid atau kedaluwarsa: {str(e)}")


from app.services.user_service import user_service


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer_optional),
) -> Optional[UserPayload]:
    """FastAPI dependency to optionally retrieve authenticated user."""
    if not credentials or not credentials.credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        return None
    google_id = payload.get("sub", "")
    current_role = user_service.get_user_role(google_id)
    return UserPayload(
        email=payload.get("email", ""),
        name=payload.get("name"),
        picture=payload.get("picture"),
        google_id=google_id,
        user_role=current_role,
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer_optional),
) -> UserPayload:
    """FastAPI dependency to require an authenticated user."""
    user = await get_current_user_optional(credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autentikasi diperlukan. Silakan sertakan token Bearer yang valid.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
