"""Simple in-process rate limiter (per client IP + path).

Good enough for a single instance / brute-force protection on auth endpoints.
For a multi-replica deployment, back this with Redis instead of a local dict.
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.core.config import settings

_hits: dict[tuple[str, str], deque] = defaultdict(deque)


def reset_rate_limits() -> None:
    _hits.clear()


class RateLimiter:
    """FastAPI dependency: allow `times` requests per `seconds` window."""

    def __init__(self, times: int, seconds: int) -> None:
        self.times = times
        self.seconds = seconds

    def __call__(self, request: Request) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return
        ip = request.client.host if request.client else "unknown"
        key = (ip, request.url.path)
        now = time.monotonic()
        bucket = _hits[key]
        while bucket and now - bucket[0] > self.seconds:
            bucket.popleft()
        if len(bucket) >= self.times:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Prea multe încercări. Încearcă din nou mai târziu.",
            )
        bucket.append(now)
