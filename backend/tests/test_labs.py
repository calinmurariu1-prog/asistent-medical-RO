"""Tests for Module 5 - Lab interpretation, series and explanations (mock AI)."""
from __future__ import annotations

API = "/api/v1"


def _auth_headers(client, email="lab@example.com"):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    tokens = client.post(
        f"{API}/auth/login", json={"email": email, "password": "Parola1234"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _add(client, h, **kw):
    payload = {"analyte": "Glicemie", "unit": "mg/dL", "ref_low": 70, "ref_high": 99}
    payload.update(kw)
    return client.post(f"{API}/labs", headers=h, json=payload)


def test_manual_add_computes_flag(client):
    h = _auth_headers(client)
    r = _add(client, h, value=120, measured_on="2026-01-10")
    assert r.status_code == 201, r.text
    assert r.json()["flag"] == "high"  # 120 > 99 but < 99*1.5 -> high, not critical


def test_series_and_trend(client):
    h = _auth_headers(client)
    _add(client, h, value=120, measured_on="2026-01-10")
    _add(client, h, value=90, measured_on="2026-03-10")

    r = client.get(f"{API}/labs/series/Glicemie", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert [p["value"] for p in body["points"]] == [120, 90]  # chronological
    assert "scădere" in body["trend"]


def test_summary_counts_abnormal(client):
    h = _auth_headers(client)
    _add(client, h, value=120, measured_on="2026-01-10")            # high
    _add(client, h, analyte="TSH", unit="uUI/mL", ref_low=0.27,
         ref_high=4.2, value=2.0, measured_on="2026-01-10")         # normal

    body = client.get(f"{API}/labs/summary", headers=h).json()
    assert body["total_analytes"] == 2
    assert body["abnormal_count"] == 1  # only Glicemie latest is abnormal


def test_analytes_distinct(client):
    h = _auth_headers(client)
    _add(client, h, value=120, measured_on="2026-01-10")
    _add(client, h, value=90, measured_on="2026-02-10")
    _add(client, h, analyte="TSH", value=2.0)
    assert client.get(f"{API}/labs/analytes", headers=h).json() == ["Glicemie", "TSH"]


def test_explain_populates_reference_and_disclaimer(client):
    h = _auth_headers(client)
    rid = _add(client, h, value=120, measured_on="2026-01-10").json()["id"]
    r = client.post(f"{API}/labs/{rid}/explain", headers=h)
    assert r.status_code == 200, r.text
    explanation = r.json()["ai_explanation"]
    assert "Glicemie" in explanation
    assert "peste intervalul" in explanation
    assert "NU reprezintă" in explanation  # disclaimer present


def test_series_unknown_analyte_404(client):
    h = _auth_headers(client)
    assert client.get(f"{API}/labs/series/Inexistent", headers=h).status_code == 404


def test_labs_isolated_per_patient(client):
    h1 = _auth_headers(client, "l1@example.com")
    h2 = _auth_headers(client, "l2@example.com")
    rid = _add(client, h1, value=120).json()["id"]
    assert client.get(f"{API}/labs", headers=h2).json() == []
    assert client.post(f"{API}/labs/{rid}/explain", headers=h2).status_code == 404
