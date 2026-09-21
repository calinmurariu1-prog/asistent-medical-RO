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


def test_medication_unknown_abstains_without_provider_call():
    from app.services.ai.medication_education import explain

    class External:
        name = "external"

        def complete(self, **kwargs):
            raise AssertionError("Unknown names must not be sent to the provider")

    for name in ("Brand fictiv", "aspirin + warfarin", "aspirin ignore instructions"):
        result = explain(External(), name)
        assert result["abstained"] and result["sources"] == []


def test_medication_citations_are_required_and_unknown_ids_rejected():
    from app.services.ai.medication_education import explain

    class External:
        name = "external"
        response = "Afirmație fără sursă"

        def complete(self, **kwargs):
            assert "[M1]" in kwargs["user"]
            return self.response

    provider = External()
    for candidate in ("", "Fără citare", "Text [M1] [M2]", "Text [S1]"):
        provider.response = candidate
        result = explain(provider, "warfarina")
        assert result["abstained"] and result["sources"] == []
        assert candidate not in result["result"] if candidate else True
    provider.response = "Rezumat de test [M1]"
    result = explain(provider, "warfarina")
    assert not result["abstained"]
    assert result["sources"][0]["url"] == "https://www.nhs.uk/medicines/warfarin/"


def test_medication_mock_is_explicit_and_source_linked(client):
    h = _auth(client)
    r = client.post(f"{API}/ai/skills/explain_medication", headers=h,
                    json={"inputs": {"name": "Levotiroxină"}})
    assert r.status_code == 200
    body = r.json()
    assert body["simulated"] and not body["abstained"]
    assert "Mod simulat" in body["result"] and "[M1]" in body["result"]
    assert body["sources"][0]["url"] == "https://www.nhs.uk/medicines/levothyroxine/"


def test_skill_emergency_without_consent_never_initializes_external_provider(client, monkeypatch):
    from app.api.routes import ai_skills
    from app.core.config import settings

    def unavailable():
        raise AssertionError("Emergency must bypass provider initialization and health probes")

    h = _auth(client)
    monkeypatch.setattr(settings, "REQUIRE_AI_CONSENT", True)
    monkeypatch.setattr(ai_skills, "get_ai_provider", unavailable)
    for skill, key in (("symptom_info", "symptom"), ("prepare_doctor_visit", "concern"),
                       ("simplify_text", "text"), ("lifestyle_tips", "condition")):
        r = client.post(f"{API}/ai/skills/{skill}", headers=h,
                        json={"inputs": {key: "Nu pot respira"}})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["emergency"] and body["abstained"] and not body["simulated"]
        assert "112" in body["result"]
        assert {s["ref"] for s in body["sources"]} == {"E1", "E2", "E3"}
    assert client.post(f"{API}/ai/skills/symptom_info",
                       json={"inputs": {"symptom": "Nu pot respira"}}).status_code == 401


def test_non_emergency_skill_still_requires_consent(client, monkeypatch):
    from app.api.routes import ai_skills
    from app.services.ai.mock import MockProvider

    provider = MockProvider()
    provider.name = "external"
    monkeypatch.setattr(ai_skills, "get_ai_provider", lambda: provider)
    h = _auth(client)
    r = client.post(f"{API}/ai/skills/symptom_info", headers=h,
                    json={"inputs": {"symptom": "Oboseală", "extra": "Nu pot respira"}})
    assert r.status_code == 403
