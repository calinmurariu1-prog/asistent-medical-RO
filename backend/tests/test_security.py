"""Tests for security headers and rate limiting."""
from __future__ import annotations

import pytest

from app.core.config import Settings, settings, validate_production_config
from app.core.rate_limit import reset_rate_limits

API = "/api/v1"


def test_field_encryption_works_with_arbitrary_key(monkeypatch):
    """Any passphrase must yield a usable Fernet key (regression: CI key was
    valid base64 but not 32 bytes and crashed encryption)."""
    from app.core import security

    for key in ("short", "ci-encryption-key-please-change-00000000", "a passphrase!"):
        monkeypatch.setattr(security.settings, "DATA_ENCRYPTION_KEY", key)
        enc = security.encrypt_field("CNP1234567890")
        assert enc and enc != "CNP1234567890"
        assert security.decrypt_field(enc) == "CNP1234567890"


def test_database_url_normalized_for_managed_hosts():
    assert (
        Settings(DATABASE_URL="postgres://u:p@h:5432/db").DATABASE_URL
        == "postgresql+psycopg://u:p@h:5432/db"
    )
    assert (
        Settings(DATABASE_URL="postgresql://u:p@h/db").DATABASE_URL
        == "postgresql+psycopg://u:p@h/db"
    )
    # Already-qualified and sqlite URLs are left untouched.
    assert Settings(DATABASE_URL="sqlite://").DATABASE_URL == "sqlite://"
    assert (
        Settings(DATABASE_URL="postgresql+psycopg://x/y").DATABASE_URL
        == "postgresql+psycopg://x/y"
    )


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


def test_api_success_auth_and_validation_responses_are_not_cacheable(client):
    from tests.test_gdpr import _auth

    headers = _auth(client, "cache-privacy@example.com")
    responses = [
        client.get(f"{API}/patients/me", headers=headers),
        client.get(f"{API}/patients/me"),
        client.put(f"{API}/patients/me", headers=headers, json={"birth_date": "invalid"}),
        client.post(f"{API}/auth/login", json={
            "email": "cache-privacy@example.com", "password": "Parola1234"}),
        client.get(f"{API}/route-does-not-exist"),
    ]
    assert [response.status_code for response in responses] == [200, 401, 422, 200, 404]
    for response in responses:
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["pragma"] == "no-cache"
        assert response.headers["expires"] == "0"


def test_validation_does_not_echo_passwords_codes_or_medical_input(client):
    from tests.test_gdpr import _auth

    password = "secret-password-marker-" * 10
    response = client.post(f"{API}/auth/register", json={
        "email": "private-validation@example.com", "password": password})
    assert response.status_code == 422
    assert password not in response.text
    assert response.json()["detail"][0]["loc"] == ["body", "password"]
    headers = _auth(client, "private-validation-owner@example.com")
    identifier = "private-identifier-marker"
    response = client.put(f"{API}/patients/me", headers=headers, json={"cnp": identifier})
    assert response.status_code == 422
    assert identifier not in response.text
    code = "private-mfa-code-marker-" * 10
    response = client.post(f"{API}/gdpr/export/with-identifier", headers=headers,
                           json={"password": "Parola1234", "mfa_code": code, "include_cnp": True})
    assert response.status_code == 422
    assert code not in response.text
    for error in response.json()["detail"]:
        assert set(error) == {"loc", "type", "msg"}
    malformed = client.post(f"{API}/auth/login", content='{ "password": "private-json-marker"',
                            headers={"Content-Type": "application/json"})
    assert malformed.status_code == 422
    assert "private-json-marker" not in malformed.text
