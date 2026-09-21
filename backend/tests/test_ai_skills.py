"""Tests for the AI skills framework (mock provider)."""
from __future__ import annotations

from datetime import UTC

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


def test_uncatalogued_conditions_and_symptoms_abstain_without_completion():
    from app.services.ai.grounded_skills import run

    class Unavailable:
        name = "external"

        def complete(self, **kwargs):
            raise AssertionError("No source must mean no model call")

    for skill, inputs in (("lifestyle_tips", {"condition": "boală fictivă"}),
                          ("symptom_info", {"symptom": "oboseala cu alte simptome"})):
        result = run(Unavailable(), skill, inputs)
        assert result["abstained"] and result["sources"] == []
    local = run(Unavailable(), "prepare_doctor_visit", {"concern": "temă fictivă"})
    assert "Fișă locală" in local["result"] and "temă fictivă" in local["result"]
    assert not local["simulated"]


def test_grounded_skill_drops_missing_or_fabricated_citations():
    from app.services.ai.grounded_skills import run

    class External:
        name = "external"
        response = "Afirmație fără sursă"

        def complete(self, **kwargs):
            assert "Sursa [T1]" in kwargs["user"]
            return self.response

    provider = External()
    for name, inputs in (("lifestyle_tips", {"condition": "diabet tip 2"}),
                         ("symptom_info", {"symptom": "cefalee"}),
                         ("simplify_text", {"text": "Text de probă. Nu adăuga fapte."})):
        for candidate in ("", "Fără sursă", "Text [T1] [T2]", "Text [S1]"):
            provider.response = candidate
            result = run(provider, name, inputs)
            assert result["abstained"] and result["sources"] == []
        provider.response = "Reformulare de probă [T1]"
        result = run(provider, name, inputs)
        assert not result["abstained"] and result["sources"][0]["ref"] == "T1"


def test_mock_simplification_keeps_full_original_and_labels_unverified_input(client):
    h = _auth(client)
    original = "Text fictiv. " * 30 + "NU se modifică tratamentul."
    r = client.post(f"{API}/ai/skills/simplify_text", headers=h,
                    json={"inputs": {"text": original}})
    assert r.status_code == 200
    body = r.json()
    assert original in body["result"]
    assert body["simulated"] and body["abstained"]
    assert body["sources"][0]["kind"] == "user_input"
    assert body["sources"][0]["url"] is None


def test_review_uses_declared_substances_and_reports_unassessed_pairs(client):
    h = _auth(client)
    r = client.post(f"{API}/ai/skills/review_prescription", headers=h,
                    json={"inputs": {"medications": "warfarin; aspirin; Brand fictiv 10 mg"}})
    assert r.status_code == 200
    body = r.json()
    assert body["abstained"] and "Perechi neevaluate: 2" in body["result"]
    assert "Brand fictiv 10 mg" in body["result"]
    assert body["sources"][0]["url"] == "https://www.nhs.uk/medicines/warfarin/"
    assert "[R1]" in body["result"]


def test_skill_input_limits_prevent_unbounded_prompts(client):
    h = _auth(client)
    for inputs in ({"text": "x" * 12001}, {str(i): "x" for i in range(9)},
                   {"x" * 65: "x"}):
        assert client.post(f"{API}/ai/skills/simplify_text", headers=h,
                           json={"inputs": inputs}).status_code == 422


def test_lifestyle_mock_has_public_source_and_no_personal_schedule(client):
    h = _auth(client)
    r = client.post(f"{API}/ai/skills/lifestyle_tips", headers=h,
                    json={"inputs": {"condition": "Diabet zaharat tip 2"}})
    assert r.status_code == 200
    body = r.json()
    assert body["simulated"] and "[T1]" in body["result"]
    assert "30 min" not in body["result"]
    assert body["sources"][0]["url"].endswith("/type-2-diabetes/treatment/")


def test_single_unverified_comparison_does_not_disclose_number(client, db_session):
    from app.models.document import LabResult

    h = _auth(client)
    item = client.post(f"{API}/labs", headers=h, json={
        "analyte": "Test fictiv", "value": 987654, "unit": "mg/dL",
        "measured_on": "2026-01-10"}).json()
    row = db_session.get(LabResult, item["id"])
    row.confidence = "unverified"
    db_session.commit()
    body = client.post(f"{API}/ai/compare-analyte", headers=h,
                       json={"analyte": "Test fictiv"}).json()
    assert body["abstained"] and "987654" not in body["result"]
    summary = client.post(f"{API}/ai/summarize-record", headers=h).json()
    assert "987654" not in summary["result"]
    assert "de confirmat" in summary["result"]


def test_empty_record_never_calls_model_and_missing_citation_abstains(client, db_session):
    from sqlalchemy import select

    from app.models.patient import Patient
    from app.services.ai import record_ai

    h = _auth(client)
    client.post(f"{API}/ai/summarize-record", headers=h)
    patient = db_session.scalar(select(Patient))

    class External:
        name = "external"
        calls = 0
        response = "Fără citare"

        def complete(self, **kwargs):
            self.calls += 1
            return self.response

    provider = External()
    assert record_ai.summarize_record(db_session, provider, patient)["abstained"]
    assert provider.calls == 0
    from app.models.medication import Medication

    med = Medication(patient_id=patient.id, name="Fictiv")
    db_session.add(med)
    db_session.commit()
    for candidate in ("Fără citare", "Text [M999999]", f"Text [M{med.id}] [S9]"):
        provider.response = candidate
        body = record_ai.summarize_record(db_session, provider, patient)
        assert body["abstained"] and body["sources"] == []
    provider.response = f"Medicament înregistrat [M{med.id}]"
    body = record_ai.summarize_record(db_session, provider, patient)
    assert not body["abstained"] and body["sources"][0]["record_id"] == med.id


def test_record_summary_sections_owner_isolation_and_partial_disclosure(client, db_session):
    from datetime import date, datetime

    from sqlalchemy import select

    from app.models.appointment import Appointment
    from app.models.clinical import MedicalHistory
    from app.models.document import Document
    from app.models.enums import MedicalEventType
    from app.models.medication import Medication
    from app.models.patient import Allergy, Patient, Vaccine

    h = _auth(client)
    client.post(f"{API}/ai/summarize-record", headers=h)
    patient = db_session.scalar(select(Patient))
    other = _auth(client, "other-record@example.com")
    client.post(f"{API}/medications", headers=other, json={"name": "OTHER-PATIENT-SECRET"})
    db_session.add_all([
        Allergy(patient_id=patient.id, substance="Alergen fictiv"),
        Vaccine(patient_id=patient.id, name="Vaccin fictiv", administered_on=date(2026, 1, 1)),
        MedicalHistory(patient_id=patient.id, event_type=MedicalEventType.OBSERVATION,
                       title="Observație fictivă"),
        Appointment(patient_id=patient.id, title="Programare fictivă",
                    starts_at=datetime(2030, 1, 1, tzinfo=UTC)),
        Document(patient_id=patient.id, original_filename="test.pdf", storage_key="fictiv"),
    ])
    db_session.add_all(Medication(patient_id=patient.id, name=f"Fictiv {i}") for i in range(21))
    db_session.commit()
    r = client.post(f"{API}/ai/summarize-record", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["truncated"] and "Rezumat parțial" in body["result"]
    assert "OTHER-PATIENT-SECRET" not in body["result"]
    assert {s["kind"] for s in body["sources"]} == {
        "alergie", "vaccin", "istoric", "programare", "document", "medicație"}
    assert sum(s["kind"] == "medicație" for s in body["sources"]) == 20
