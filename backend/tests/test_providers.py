"""Tests for the nearby-doctor finder (mock places provider)."""
from __future__ import annotations

API = "/api/v1"


def _auth(client, email="prov@example.com"):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    tokens = client.post(
        f"{API}/auth/login", json={"email": email, "password": "Parola1234"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _abnormal_glicemie(client, h):
    client.post(f"{API}/labs", headers=h, json={
        "analyte": "Glicemie", "value": 150, "unit": "mg/dL",
        "ref_low": 70, "ref_high": 99, "measured_on": "2026-01-10"})


def test_suggested_specialties_from_abnormal_lab(client):
    h = _auth(client)
    _abnormal_glicemie(client, h)
    body = client.get(f"{API}/providers/suggested-specialties", headers=h).json()
    specs = {s["specialty"] for s in body}
    assert "Diabetolog" in specs
    diab = next(s for s in body if s["specialty"] == "Diabetolog")
    assert any("Glicemie" in r for r in diab["reasons"])


def test_suggested_specialties_default_when_empty(client):
    h = _auth(client)
    body = client.get(f"{API}/providers/suggested-specialties", headers=h).json()
    assert body == [{"specialty": "Medic de familie",
                     "reasons": ["Nicio problemă specifică detectată în date."]}]


def test_nearby_with_coords_and_specialty(client):
    h = _auth(client)
    r = client.get(
        f"{API}/providers/nearby?lat=44.43&lng=26.10&specialty=Cardiolog&radius_m=6000",
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["specialty"] == "Cardiolog"
    assert body["provider_source"] == "mock"
    assert len(body["results"]) > 0
    dists = [p["distance_km"] for p in body["results"]]
    assert dists == sorted(dists)                       # sorted by distance
    assert all(d * 1000 <= 6000 for d in dists)         # within radius
    assert "informativ" in body["disclaimer"]


def test_nearby_auto_specialty_from_record(client):
    h = _auth(client)
    _abnormal_glicemie(client, h)
    r = client.get(f"{API}/providers/nearby?lat=44.43&lng=26.10", headers=h)
    assert r.json()["specialty"] == "Diabetolog"


def test_nearby_city_fallback(client):
    h = _auth(client)
    r = client.get(f"{API}/providers/nearby?city=Bucuresti&specialty=Nefrolog", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["center"]["lat"] != 0
    assert body["results"]


def test_nearby_requires_location(client):
    h = _auth(client)
    r = client.get(f"{API}/providers/nearby?specialty=Cardiolog", headers=h)
    assert r.status_code == 400
