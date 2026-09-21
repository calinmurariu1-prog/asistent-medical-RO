"""Tests for token revocation, email hooks and AI-consent enforcement."""
from __future__ import annotations

from app.core.config import settings
from app.services.token_service import PASSWORD_RESET, create_purpose_token

API = "/api/v1"


def _register(client, email="sec@example.com"):
    return client.post(
        f"{API}/auth/register", json={"email": email, "password": "Parola1234"}
    ).json()


def _login(client, email="sec@example.com", password="Parola1234"):
    tokens = client.post(
        f"{API}/auth/login", json={"email": email, "password": password}
    ).json()
    return tokens, {"Authorization": f"Bearer {tokens['access_token']}"}


def test_register_sends_verification_email(client, monkeypatch):
    calls = {}
    monkeypatch.setattr(
        "app.api.routes.auth.send_verification_email",
        lambda to, token: calls.update(to=to, token=token),
    )
    _register(client, "verify@example.com")
    assert calls["to"] == "verify@example.com"
    assert calls["token"]


def test_logout_all_revokes_existing_tokens(client):
    _register(client)
    _tokens, h = _login(client)
    assert client.get(f"{API}/auth/me", headers=h).status_code == 200

    assert client.post(f"{API}/auth/logout-all", headers=h).status_code == 200
    # The old access token no longer resolves (token_version bumped).
    assert client.get(f"{API}/auth/me", headers=h).status_code == 401


def test_refresh_rejected_after_logout_all(client):
    _register(client)
    tokens, h = _login(client)
    client.post(f"{API}/auth/logout-all", headers=h)
    r = client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 401


def test_password_reset_invalidates_sessions(client):
    user = _register(client, "reset@example.com")
    _tokens, h = _login(client, "reset@example.com")

    token = create_purpose_token(str(user["id"]), PASSWORD_RESET)
    r = client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token, "new_password": "ParolaNoua1"},
    )
    assert r.status_code == 200
    # Old session is dead; new password works.
    assert client.get(f"{API}/auth/me", headers=h).status_code == 401
    assert _login(client, "reset@example.com", "ParolaNoua1")[0]["access_token"]


def test_mfa_secret_encrypted_and_login_flow(client, db_session):
    import pyotp
    from sqlalchemy import select

    from app.models.user import User

    _register(client, "mfa@example.com")
    _tokens, h = _login(client, "mfa@example.com")

    secret = client.post(f"{API}/auth/mfa/setup", headers=h).json()["secret"]
    # Stored value must be the ciphertext, not the raw TOTP secret.
    stored = db_session.scalar(
        select(User).where(User.email == "mfa@example.com")
    ).mfa_secret
    assert stored and stored != secret

    code = pyotp.TOTP(secret).now()
    r = client.post(f"{API}/auth/mfa/activate", headers=h, json={"code": code})
    assert r.status_code == 200

    # Login now requires the MFA code.
    r = client.post(f"{API}/auth/login",
                    json={"email": "mfa@example.com", "password": "Parola1234"})
    assert r.status_code == 401
    r = client.post(f"{API}/auth/login", json={
        "email": "mfa@example.com", "password": "Parola1234",
        "mfa_code": pyotp.TOTP(secret).now()})
    assert r.status_code == 200


def test_ai_consent_enforced_when_enabled(client, monkeypatch):
    monkeypatch.setattr(settings, "REQUIRE_AI_CONSENT", True)
    _register(client, "consent@example.com")
    _tokens, h = _login(client, "consent@example.com")
    chat_id = client.post(f"{API}/chats", headers=h, json={}).json()["id"]

    # No consent yet -> blocked.
    r = client.post(f"{API}/chats/{chat_id}/messages", headers=h, json={"content": "salut"})
    assert r.status_code == 403

    # Grant AI consent -> allowed.
    client.post(f"{API}/gdpr/consents", headers=h,
                json={"consent_type": "ai_processing", "granted": True})
    r = client.post(f"{API}/chats/{chat_id}/messages", headers=h, json={"content": "salut"})
    assert r.status_code == 200


def test_swagger_login_rejects_disabled_account(client, db_session):
    from app.models.user import User
    user = _register(client)
    account = db_session.get(User, user["id"])
    account.is_active = False
    db_session.commit()
    response = client.post(f"{API}/auth/login-form", data={
        "username": "sec@example.com", "password": "Parola1234"
    })
    assert response.status_code == 403
    assert "access_token" not in response.json()


def test_swagger_login_cannot_bypass_mfa(client):
    import pyotp
    _register(client)
    _, headers = _login(client)
    secret = client.post(f"{API}/auth/mfa/setup", headers=headers).json()["secret"]
    assert client.post(f"{API}/auth/mfa/activate", headers=headers,
                       json={"code": pyotp.TOTP(secret).now()}).status_code == 200
    response = client.post(f"{API}/auth/login-form", data={
        "username": "sec@example.com", "password": "Parola1234"
    })
    assert response.status_code == 401
    assert "access_token" not in response.json()


def test_swagger_login_ordinary_account(client):
    _register(client)
    response = client.post(f"{API}/auth/login-form", data={
        "username": "sec@example.com", "password": "Parola1234"
    })
    assert response.status_code == 200
    assert client.get(f"{API}/auth/me", headers={
        "Authorization": "Bearer " + response.json()["access_token"]
    }).status_code == 200


def test_swagger_login_invalid_username(client):
    response = client.post(f"{API}/auth/login-form", data={
        "username": "not-an-email", "password": "invalid"
    })
    assert response.status_code == 401


def test_swagger_login_is_rate_limited(client, monkeypatch):
    from app.api.routes.auth import _auth_limiter
    from app.core.rate_limit import reset_rate_limits
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(_auth_limiter, "times", 2)
    reset_rate_limits()
    try:
        form = {"username": "missing@example.com", "password": "invalid"}
        assert client.post(f"{API}/auth/login-form", data=form).status_code == 401
        assert client.post(f"{API}/auth/login-form", data=form).status_code == 401
        assert client.post(f"{API}/auth/login-form", data=form).status_code == 429
    finally:
        reset_rate_limits()
