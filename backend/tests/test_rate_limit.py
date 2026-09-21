from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core import rate_limit
from app.core.config import settings


def request(ip="127.0.0.1", path="/auth/login"):
    return Request({"type": "http", "method": "POST", "scheme": "http", "path": path,
                    "query_string": b"", "headers": [], "client": (ip, 1234),
                    "server": ("localhost", 80)})


@pytest.fixture(autouse=True)
def reset(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    rate_limit.reset_rate_limits()
    yield
    rate_limit.reset_rate_limits()


def test_concurrent_attempts_do_not_exceed_limit():
    limiter = rate_limit.RateLimiter(3, 60)
    barrier = Barrier(12)

    def attempt(_):
        barrier.wait()
        try:
            limiter(request())
            return True
        except HTTPException as error:
            assert error.status_code == 429
            assert int(error.headers["Retry-After"]) > 0
            return False

    with ThreadPoolExecutor(max_workers=12) as pool:
        assert sum(pool.map(attempt, range(12))) == 3


def test_window_expiry_and_inactive_bucket_cleanup(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: clock[0])
    limiter = rate_limit.RateLimiter(1, 10)
    limiter(request())
    clock[0] = 109.1
    with pytest.raises(HTTPException) as error:
        limiter(request())
    assert error.value.headers["Retry-After"] == "1"
    clock[0] = 110.1
    limiter(request("127.0.0.2"))
    assert len(rate_limit._hits) == 1
    limiter(request())


def test_bucket_capacity_fails_closed_without_erasing_active_history(monkeypatch):
    monkeypatch.setattr(rate_limit, "MAX_BUCKETS", 2)
    limiter = rate_limit.RateLimiter(1, 60)
    limiter(request("127.0.0.1"))
    limiter(request("127.0.0.2"))
    for ip in ["127.0.0.3", "127.0.0.1"]:
        with pytest.raises(HTTPException) as error:
            limiter(request(ip))
        assert error.value.status_code == 429
    assert len(rate_limit._hits) == 2
