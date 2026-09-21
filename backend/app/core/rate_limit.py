"""Bounded, thread-safe in-process limits; replicas still require a shared backend."""
import math
import time
from collections import deque
from threading import Lock

from fastapi import HTTPException, Request, status

from app.core.config import settings

MAX_BUCKETS = 10_000
_hits: dict[tuple[str, str, int], deque[float]] = {}
_lock = Lock()
_next_sweep = 0.0


def reset_rate_limits() -> None:
    global _next_sweep
    with _lock:
        _hits.clear()
        _next_sweep = 0.0


def _reject(retry: float) -> None:
    raise HTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "Prea multe încercări. Încearcă din nou mai târziu.",
        headers={"Retry-After": str(max(1, math.ceil(retry))), "Cache-Control": "no-store"},
    )


class RateLimiter:
    """Allow at most `times` requests in a rolling `seconds` window per IP/path."""

    def __init__(self, times: int, seconds: int) -> None:
        if times < 1 or seconds < 1:
            raise ValueError("Rate limits must be positive")
        self.times = times
        self.seconds = seconds

    def __call__(self, request: Request) -> None:
        global _next_sweep
        if not settings.RATE_LIMIT_ENABLED:
            return
        ip = request.client.host if request.client else "unknown"
        key = (ip, request.url.path, self.seconds)
        with _lock:
            now = time.monotonic()
            if now >= _next_sweep:
                expired = [k for k, hits in _hits.items()
                           if not hits or hits[-1] + k[2] <= now]
                for expired_key in expired:
                    del _hits[expired_key]
                _next_sweep = now + 1
            bucket = _hits.get(key)
            if bucket is None:
                if len(_hits) >= MAX_BUCKETS:
                    # Do not evict active histories: churn must not reset limits.
                    _reject(1)
                bucket = _hits[key] = deque()
            while bucket and bucket[0] + self.seconds <= now:
                bucket.popleft()
            if len(bucket) >= self.times:
                _reject(bucket[0] + self.seconds - now)
            bucket.append(now)
