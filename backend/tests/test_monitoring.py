"""Tests for Module 8 - Chronic disease monitoring dashboard."""
from __future__ import annotations

API = "/api/v1"


def _auth(client, email="mon@example.com"):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    tokens = client.post(
        f"{API}/auth/login", json={"email": email, "password": "Parola1234"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _lab(client, h, analyte, value, measured_on, **kw):
    return client.post(
        f"{API}/labs",
        headers=h,
        json={"analyte": analyte, "value": value, "measured_on": measured_on, **kw},
    )


def test_dashboard_groups_recognized_analytes(client):
    h = _auth(client)
    _lab(client, h, "Glicemie", 130, "2026-01-10", unit="mg/dL", ref_low=70, ref_high=99)
    _lab(client, h, "Glicemie", 110, "2026-03-10", unit="mg/dL", ref_low=70, ref_high=99)
    _lab(client, h, "HbA1c", 7.2, "2026-03-10", unit="%")
    _lab(client, h, "AnalitNecunoscut", 5, "2026-03-10")  # ignored by monitoring

    body = client.get(f"{API}/monitoring/dashboard", headers=h).json()
    assert "Diabet" in body["groups"]
    labels = {p["label"] for p in body["groups"]["Diabet"]}
    assert labels == {"Glicemie", "HbA1c"}

    glicemie = next(p for p in body["groups"]["Diabet"] if p["label"] == "Glicemie")
    assert len(glicemie["points"]) == 2
    assert "scădere" in glicemie["trend"]
    # Unrecognized analyte forms no group.
    assert all("AnalitNecunoscut" not in g for g in body["groups"])


def test_dashboard_computes_bmi_from_profile(client):
    h = _auth(client)
    client.put(
        f"{API}/patients/me", headers=h, json={"weight_kg": 80, "height_cm": 180}
    )
    body = client.get(f"{API}/monitoring/dashboard", headers=h).json()
    assert body["bmi"] == 24.7
    assert body["chronic_conditions"] == []


def test_supported_parameters(client):
    h = _auth(client)
    params = client.get(f"{API}/monitoring/parameters", headers=h).json()
    assert params["Glicemie"] == "Diabet"
    assert params["TSH"] == "Tiroidă"
