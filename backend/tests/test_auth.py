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
