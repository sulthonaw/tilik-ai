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
