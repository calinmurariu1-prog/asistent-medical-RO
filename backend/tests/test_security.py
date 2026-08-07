"""Tests for security headers and rate limiting."""
from __future__ import annotations

import pytest

from app.core.config import Settings, settings, validate_production_config
from app.core.rate_limit import reset_rate_limits

API = "/api/v1"


def test_production_config_rejects_weak_secrets():
    weak = Settings(
        ENVIRONMENT="production", SECRET_KEY="change-me", DATA_ENCRYPTION_KEY=""
    )
    with pytest.raises(RuntimeError):
        validate_production_config(weak)

    strong = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="x" * 40,
        DATA_ENCRYPTION_KEY="a-real-encryption-key-value-here",
    )
    validate_production_config(strong)  # must not raise

    # Weak secrets are allowed in development.
    dev = Settings(
        ENVIRONMENT="development", SECRET_KEY="change-me", DATA_ENCRYPTION_KEY=""
    )
    validate_production_config(dev)


def test_security_headers_present(client):
    r = client.get("/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert "referrer-policy" in r.headers


def test_login_rate_limited(client, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    reset_rate_limits()

    payload = {"email": "nobody@example.com", "password": "wrong"}
    limit = settings.RATE_LIMIT_LOGIN_TIMES
    statuses = [
        client.post(f"{API}/auth/login", json=payload).status_code
        for _ in range(limit + 1)
    ]
    assert statuses[:limit] == [401] * limit  # allowed (bad creds)
    assert statuses[limit] == 429            # blocked by the limiter
    reset_rate_limits()
