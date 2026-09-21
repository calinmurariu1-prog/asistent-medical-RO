"""Tests for Module 1 - Authentication."""
from __future__ import annotations

API = "/api/v1"


def _register(client, email="ana@example.com", password="Parola1234"):
    return client.post(
        f"{API}/auth/register",
        json={"email": email, "password": password, "full_name": "Ana Pop"},
    )


def test_register_and_login_flow(client):
    r = _register(client)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == "ana@example.com"
    assert body["role"] == "patient"
    assert body["is_email_verified"] is False

    # Duplicate registration is rejected.
    assert _register(client).status_code == 409

    # Login returns a token pair.
    r = client.post(
        f"{API}/auth/login",
        json={"email": "ana@example.com", "password": "Parola1234"},
    )
    assert r.status_code == 200, r.text
    tokens = r.json()
    assert tokens["access_token"] and tokens["refresh_token"]

    # /me works with the access token.
    r = client.get(
        f"{API}/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 200
    assert r.json()["email"] == "ana@example.com"


def test_login_wrong_password(client):
    _register(client)
    r = client.post(
        f"{API}/auth/login",
        json={"email": "ana@example.com", "password": "gresit"},
    )
    assert r.status_code == 401


def test_refresh_token(client):
    _register(client)
    tokens = client.post(
        f"{API}/auth/login",
        json={"email": "ana@example.com", "password": "Parola1234"},
    ).json()
    r = client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_me_requires_auth(client):
    assert client.get(f"{API}/auth/me").status_code == 401


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_mfa_activation_revokes_old_sessions_and_cannot_replace_active_secret(client, db_session):
    import pyotp
    from sqlalchemy import select

    from app.core.security import decrypt_field
    from app.models.user import AuditLog, User

    _register(client)
    credentials = {"email": "ana@example.com", "password": "Parola1234"}
    old = client.post(f"{API}/auth/login", json=credentials).json()
    headers = {"Authorization": f"Bearer {old['access_token']}"}
    setup = client.post(f"{API}/auth/mfa/setup", headers=headers)
    assert setup.status_code == 200
    secret = setup.json()["secret"]
    code = pyotp.TOTP(secret).now()
    assert client.post(f"{API}/auth/mfa/activate", headers=headers,
                       json={"code": code}).status_code == 200
    assert client.get(f"{API}/auth/me", headers=headers).status_code == 401
    assert client.post(f"{API}/auth/refresh",
                       json={"refresh_token": old["refresh_token"]}).status_code == 401
    assert client.post(f"{API}/auth/login", json=credentials).status_code == 401
    fresh = client.post(f"{API}/auth/login", json={**credentials, "mfa_code": code})
    assert fresh.status_code == 200
    headers = {"Authorization": f"Bearer {fresh.json()['access_token']}"}
    assert client.post(f"{API}/auth/mfa/setup", headers=headers).status_code == 409
    assert client.post(f"{API}/auth/mfa/activate", headers=headers,
                       json={"code": code}).status_code == 409
    user = db_session.scalar(select(User).where(User.email == credentials["email"]))
    db_session.refresh(user)
    assert decrypt_field(user.mfa_secret) == secret
    events = db_session.scalars(select(AuditLog).where(AuditLog.action.like("mfa_%"))).all()
    assert {e.action for e in events} == {"mfa_setup", "mfa_activate"}
    assert len(events) == 2
    assert all(e.detail is None for e in events)


def test_mfa_activation_rejects_replaced_setup_snapshot(client, db_session, monkeypatch):
    import pyotp
    from sqlalchemy import select, update

    from app.core.security import decrypt_field, encrypt_field
    from app.models.user import User

    _register(client)
    tokens = client.post(f"{API}/auth/login", json={
        "email": "ana@example.com", "password": "Parola1234"}).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    secret = client.post(f"{API}/auth/mfa/setup", headers=headers).json()["secret"]
    replacement = pyotp.random_base32()
    verify = pyotp.TOTP.verify

    def replace_during_verification(totp, code, **kwargs):
        result = verify(totp, code, **kwargs)
        db_session.execute(update(User).execution_options(synchronize_session=False).values(
            mfa_secret=encrypt_field(replacement)))
        db_session.commit()
        return result

    monkeypatch.setattr(pyotp.TOTP, "verify", replace_during_verification)
    result = client.post(f"{API}/auth/mfa/activate", headers=headers,
                         json={"code": pyotp.TOTP(secret).now()})
    assert result.status_code == 409
    user = db_session.scalar(select(User))
    db_session.refresh(user)
    assert user.mfa_enabled is False
    assert decrypt_field(user.mfa_secret) == replacement
    assert client.get(f"{API}/auth/me", headers=headers).status_code == 200
