"""Tests for the SaaS subscription foundation (plans, entitlements, gating)."""
from __future__ import annotations

from sqlalchemy import select

from app.models.document import Document
from app.models.enums import DocumentCategory
from app.models.patient import Patient
from app.models.user import User

API = "/api/v1"


def _auth(client, email="billing@example.com"):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    tokens = client.post(
        f"{API}/auth/login", json={"email": email, "password": "Parola1234"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_plans_catalog(client):
    plans = client.get(f"{API}/billing/plans").json()
    by_plan = {p["plan"]: p for p in plans}
    assert set(by_plan) == {"free", "premium", "family"}
    assert by_plan["free"]["price_eur_month"] == 0.0
    assert by_plan["premium"]["flags"]["advanced_ai"] is True
    assert by_plan["free"]["limits"]["documents"] == 20
    assert by_plan["premium"]["limits"]["documents"] == -1


def test_default_subscription_is_free(client):
    h = _auth(client)
    sub = client.get(f"{API}/billing/subscription", headers=h).json()
    assert sub["plan"] == "free"
    assert sub["status"] == "active"
    assert sub["flags"]["advanced_ai"] is False


def test_change_plan_upgrades_entitlements(client):
    h = _auth(client)
    sub = client.post(
        f"{API}/billing/subscription", headers=h, json={"plan": "premium"}
    ).json()
    assert sub["plan"] == "premium"
    assert sub["provider"] == "manual"
    assert sub["flags"]["export"] is True
    assert sub["limits"]["documents"] == -1

    # Persisted across requests.
    again = client.get(f"{API}/billing/subscription", headers=h).json()
    assert again["plan"] == "premium"

    # Downgrade resets to free + clears billing linkage.
    down = client.post(
        f"{API}/billing/subscription", headers=h, json={"plan": "free"}
    ).json()
    assert down["plan"] == "free"
    assert down["provider"] == "none"


def test_free_document_limit_enforced(client, db_session):
    h = _auth(client, email="quota@example.com")
    # Ensure the patient exists, then pre-fill up to the free limit (20).
    user = db_session.scalar(select(User).where(User.email == "quota@example.com"))
    patient = db_session.scalar(select(Patient).where(Patient.user_id == user.id))
    if patient is None:
        patient = Patient(user_id=user.id)
        db_session.add(patient)
        db_session.commit()
    for i in range(20):
        db_session.add(
            Document(
                patient_id=patient.id,
                category=DocumentCategory.OTHER,
                original_filename=f"doc{i}.pdf",
                content_type="application/pdf",
                size_bytes=10,
                storage_key=f"key-{i}",
            )
        )
    db_session.commit()

    # 21st upload is blocked on the free plan.
    r = client.post(
        f"{API}/documents",
        headers=h,
        files={"file": ("more.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert r.status_code == 402

    # Upgrading to premium lifts the limit.
    client.post(f"{API}/billing/subscription", headers=h, json={"plan": "premium"})
    r = client.post(
        f"{API}/documents",
        headers=h,
        files={"file": ("more.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert r.status_code == 201
