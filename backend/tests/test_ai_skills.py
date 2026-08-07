"""Tests for the AI skills framework (mock provider)."""
from __future__ import annotations

API = "/api/v1"


def _auth(client, email="skills@example.com"):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    tokens = client.post(
        f"{API}/auth/login", json={"email": email, "password": "Parola1234"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_list_skills(client):
    h = _auth(client)
    skills = client.get(f"{API}/ai/skills", headers=h).json()
    names = {s["name"] for s in skills}
    assert {"explain_medication", "prepare_doctor_visit", "symptom_info"} <= names
    med = next(s for s in skills if s["name"] == "explain_medication")
    assert med["inputs"] == ["name"]


def test_run_skill_returns_result_with_disclaimer(client):
    h = _auth(client)
    r = client.post(
        f"{API}/ai/skills/explain_medication",
        headers=h,
        json={"inputs": {"name": "Metformin"}},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["skill"] == "explain_medication"
    assert "Metformin" in body["result"]
    assert "orientativ" in body["result"].lower()  # disclaimer enforced


def test_run_skill_missing_input(client):
    h = _auth(client)
    r = client.post(f"{API}/ai/skills/explain_medication", headers=h, json={"inputs": {}})
    assert r.status_code == 400
    assert "name" in r.json()["detail"]


def test_run_unknown_skill(client):
    h = _auth(client)
    r = client.post(f"{API}/ai/skills/nope", headers=h, json={"inputs": {}})
    assert r.status_code == 404


def test_prepare_doctor_visit(client):
    h = _auth(client)
    r = client.post(
        f"{API}/ai/skills/prepare_doctor_visit",
        headers=h,
        json={"inputs": {"concern": "dureri de cap frecvente"}},
    )
    assert r.status_code == 200
    assert "dureri de cap" in r.json()["result"]


def test_summarize_record(client):
    h = _auth(client)
    client.post(f"{API}/labs", headers=h, json={
        "analyte": "Glicemie", "value": 150, "unit": "mg/dL",
        "ref_low": 70, "ref_high": 99, "measured_on": "2026-01-10"})
    client.post(f"{API}/medications", headers=h, json={"name": "Metformin"})

    r = client.post(f"{API}/ai/summarize-record", headers=h)
    assert r.status_code == 200, r.text
    result = r.json()["result"]
    assert "Glicemie" in result and "Metformin" in result
    assert "orientativ" in result.lower()


def test_compare_analyte(client):
    h = _auth(client)
    for v, d in ((150, "2026-01-10"), (120, "2026-03-10")):
        client.post(f"{API}/labs", headers=h, json={
            "analyte": "Glicemie", "value": v, "unit": "mg/dL",
            "ref_low": 70, "ref_high": 99, "measured_on": d})

    r = client.post(f"{API}/ai/compare-analyte", headers=h, json={"analyte": "Glicemie"})
    assert r.status_code == 200, r.text
    assert "Glicemie" in r.json()["result"]


def test_compare_analyte_single_value(client):
    h = _auth(client)
    client.post(f"{API}/labs", headers=h, json={
        "analyte": "TSH", "value": 2.0, "unit": "uUI/mL", "measured_on": "2026-01-10"})
    r = client.post(f"{API}/ai/compare-analyte", headers=h, json={"analyte": "TSH"})
    assert r.status_code == 200
    assert "o singură măsurătoare" in r.json()["result"]
