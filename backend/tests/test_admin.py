"""Tests for Module 15 - Admin panel & feedback."""
from __future__ import annotations

from sqlalchemy import select

from app.models.enums import UserRole
from app.models.user import User

API = "/api/v1"


def _auth(client, email):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    tokens = client.post(
        f"{API}/auth/login", json={"email": email, "password": "Parola1234"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _promote(db_session, email):
    user = db_session.scalar(select(User).where(User.email == email))
    user.role = UserRole.ADMIN
    db_session.add(user)
    db_session.commit()


def test_non_admin_forbidden(client):
    h = _auth(client, "user@example.com")
    assert client.get(f"{API}/admin/stats", headers=h).status_code == 403


def test_admin_stats_and_users(client, db_session):
    _auth(client, "patient@example.com")  # a regular user exists
    h = _auth(client, "boss@example.com")
    _promote(db_session, "boss@example.com")

    stats = client.get(f"{API}/admin/stats", headers=h).json()
    assert stats["users"] == 2

    users = client.get(f"{API}/admin/users", headers=h).json()
    assert len(users) == 2


def test_admin_can_deactivate_user(client, db_session):
    uid = None
    _auth(client, "target@example.com")
    h = _auth(client, "boss@example.com")
    _promote(db_session, "boss@example.com")

    target = db_session.scalar(select(User).where(User.email == "target@example.com"))
    uid = target.id
    r = client.patch(f"{API}/admin/users/{uid}", headers=h, json={"is_active": False})
    assert r.status_code == 200
    assert r.json()["is_active"] is False


def test_audit_logs_capture_login(client, db_session):
    h = _auth(client, "boss@example.com")
    _promote(db_session, "boss@example.com")
    logs = client.get(f"{API}/admin/audit-logs", headers=h).json()
    actions = {entry["action"] for entry in logs}
    assert "login" in actions
    assert "register" in actions


def test_feedback_submit_and_admin_list(client, db_session):
    hu = _auth(client, "happy@example.com")
    r = client.post(f"{API}/feedback", headers=hu, json={"message": "Super app!", "rating": 5})
    assert r.status_code == 201

    hb = _auth(client, "boss@example.com")
    _promote(db_session, "boss@example.com")
    feedback = client.get(f"{API}/admin/feedback", headers=hb).json()
    assert len(feedback) == 1
    assert feedback[0]["rating"] == 5
