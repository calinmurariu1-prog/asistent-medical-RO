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
    assert r.json()["flag"] == "high"  # Above the supplied upper bound.


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


def test_missing_reference_and_text_result_are_not_normal(client):
    h = _auth_headers(client)
    for payload in ({"value": 90, "ref_low": None, "ref_high": None},
                    {"value_text": "pozitiv", "ref_low": None, "ref_high": None}):
        result = _add(client, h, **payload)
        assert result.status_code == 201
        assert result.json()["flag"] == "unknown"
        explained = client.post(f"{API}/labs/{result.json()['id']}/explain", headers=h).json()
        assert "Nu pot evalua" in explained["ai_explanation"]
        assert "se încadrează" not in explained["ai_explanation"]


def test_large_deviation_does_not_infer_critical_threshold(client):
    h = _auth_headers(client)
    assert _add(client, h, value=400).json()["flag"] == "high"
    assert _add(client, h, value=10).json()["flag"] == "low"


def test_invalid_manual_values_rejected(client):
    h = _auth_headers(client)
    for payload in ({"value": "NaN"}, {"value": "Infinity"},
                    {"value": 80, "ref_low": 99, "ref_high": 70},
                    {"value": 80, "analyte": "   "}, {"value": None}):
        assert _add(client, h, **payload).status_code == 422
    assert client.get(f"{API}/labs", headers=h).json() == []


def test_reference_bounds_are_inclusive_and_one_sided():
    from app.models.enums import LabFlag
    from app.services.document_processing import compute_flag

    assert compute_flag(70, 70, 99) == LabFlag.NORMAL
    assert compute_flag(99, 70, 99) == LabFlag.NORMAL
    assert compute_flag(100, None, 99) == LabFlag.HIGH
    assert compute_flag(60, 70, None) == LabFlag.LOW
    assert compute_flag(80, 99, 70) == LabFlag.UNKNOWN
    assert compute_flag(float("inf"), 70, 99) == LabFlag.UNKNOWN


def test_migration_reclassifies_old_results_and_clears_stale_explanations():
    import importlib.util
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine, text

    path = Path(__file__).parents[1] / "alembic/versions/a7c9e1f3b5d7_lab_reference_flags.py"
    spec = importlib.util.spec_from_file_location("lab_flags_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE lab_results (id INTEGER, value FLOAT, ref_low FLOAT, "
            "ref_high FLOAT, flag VARCHAR(13), ai_explanation TEXT)"))
        connection.execute(text(
            "INSERT INTO lab_results VALUES (1, 400, 70, 99, 'CRITICAL_HIGH', 'old'), "
            "(2, 90, NULL, NULL, 'NORMAL', 'old'), (3, 80, 70, 99, 'NORMAL', 'old'), "
            "(4, 10, 70, 99, 'CRITICAL_LOW', 'old')"))
        with Operations.context(MigrationContext.configure(connection)):
            module.upgrade()
        rows = connection.execute(text(
            "SELECT flag, ai_explanation FROM lab_results ORDER BY id")).all()
        assert rows == [("HIGH", None), ("UNKNOWN", None), ("NORMAL", None), ("LOW", None)]


def test_mixed_units_block_trend_and_ai_comparison(client):
    h = _auth_headers(client)
    _add(client, h, value=90, measured_on="2026-01-10")
    _add(client, h, value=5, unit="mmol/L", measured_on="2026-02-10")
    series = client.get(f"{API}/labs/series/Glicemie", headers=h).json()
    assert len(series["points"]) == 2  # History retained, chart withheld.
    assert series["trend"] is None
    assert "unitățile diferă" in series["comparison_warning"]
    comparison = client.post(f"{API}/ai/compare-analyte", headers=h,
                             json={"analyte": "Glicemie"}).json()
    assert "unitățile diferă" in comparison["result"]


def test_missing_dates_and_units_block_comparison(client):
    h = _auth_headers(client)
    _add(client, h, value=90)
    _add(client, h, value=80, measured_on="2026-02-10")
    series = client.get(f"{API}/labs/series/Glicemie", headers=h).json()
    assert series["trend"] is None
    assert "date lipsă" in series["comparison_warning"]
    _add(client, h, value=85, unit=None, measured_on="2026-03-10")
    series = client.get(f"{API}/labs/series/Glicemie", headers=h).json()
    assert "lipsesc unități" in series["comparison_warning"]


def test_changing_reference_ranges_not_applied_to_whole_chart(client):
    h = _auth_headers(client)
    _add(client, h, value=90, measured_on="2026-01-10")
    _add(client, h, value=85, ref_high=110, measured_on="2026-02-10")
    series = client.get(f"{API}/labs/series/Glicemie", headers=h).json()
    assert series["ref_low"] is None and series["ref_high"] is None
    assert "scădere" in series["trend"]


def test_unverified_values_do_not_drive_comparison_or_ai_interpretation(
    client, db_session, monkeypatch
):
    from app.models.document import LabResult
    from app.services.ai.mock import MockProvider

    h = _auth_headers(client)
    result_id = _add(client, h, value=120, measured_on="2026-01-10").json()["id"]
    row = db_session.get(LabResult, result_id)
    row.confidence = "unverified"
    db_session.commit()

    def unexpected(*args, **kwargs):
        raise AssertionError("Unconfirmed value must not be interpreted by AI")

    monkeypatch.setattr(MockProvider, "explain_lab_value", unexpected)
    summary = client.get(f"{API}/labs/summary", headers=h).json()
    assert summary["abnormal_count"] == 0
    assert summary["unknown_count"] == 1
    assert summary["items"][0]["latest_value"] is None
    series = client.get(f"{API}/labs/series/Glicemie", headers=h).json()
    assert "confirmat" in series["comparison_warning"]
    assert series["trend"] is None
    explanation = client.post(f"{API}/labs/{result_id}/explain", headers=h).json()
    assert "nu este confirmată" in explanation["ai_explanation"]


def test_manual_correction_delete_isolation_and_cache(client, db_session):
    from sqlalchemy import select

    from app.models.document import LabResult
    from app.models.user import AuditLog

    owner = _auth_headers(client, "owner-lab@example.com")
    other = _auth_headers(client, "other-lab@example.com")
    result_id = _add(client, owner, value=120).json()["id"]
    sibling_id = _add(client, owner, value=90).json()["id"]
    client.post(f"{API}/labs/{sibling_id}/explain", headers=owner)
    row = db_session.get(LabResult, result_id)
    row.confidence = "unverified"
    db_session.commit()
    payload = {"analyte": "Glicemie", "value": 85, "unit": "mg/dL",
               "ref_low": 70, "ref_high": 99, "measured_on": "2026-01-10"}
    assert client.put(f"{API}/labs/{result_id}", headers=other, json=payload).status_code == 404
    assert client.delete(f"{API}/labs/{result_id}", headers=other).status_code == 404
    response = client.put(f"{API}/labs/{result_id}", headers=owner, json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["confidence"] == "verified"
    assert response.json()["flag"] == "normal"
    assert response.json()["measured_on"] == "2026-01-10"
    assert all(r["ai_explanation"] is None for r in client.get(f"{API}/labs", headers=owner).json())
    assert client.delete(f"{API}/labs/{result_id}", headers=owner).status_code == 204
    assert [r["id"] for r in client.get(f"{API}/labs", headers=owner).json()] == [sibling_id]
    actions = list(db_session.scalars(select(AuditLog.action).where(
        AuditLog.resource_type == "lab_result", AuditLog.resource_id == str(result_id))))
    assert actions == ["lab.create", "lab.update", "lab.delete"]


def test_correction_rejects_invalid_payload_without_changing_value(client):
    headers = _auth_headers(client)
    result_id = _add(client, headers, value=120).json()["id"]
    response = client.put(f"{API}/labs/{result_id}", headers=headers,
                          json={"analyte": "Glicemie", "value": 90, "ref_low": 100, "ref_high": 70})
    assert response.status_code == 422
    assert client.get(f"{API}/labs", headers=headers).json()[0]["value"] == 120


def test_linked_lab_correction_waits_for_processing_and_preserves_original(client, db_session):
    from app.models.document import Document, LabResult
    from app.models.enums import ProcessingStatus

    headers = _auth_headers(client)
    result_id = _add(client, headers, value=120).json()["id"]
    row = db_session.get(LabResult, result_id)
    document = Document(patient_id=row.patient_id, original_filename="fictiv.pdf",
                        storage_key="private-fictiv", status=ProcessingStatus.PROCESSING)
    db_session.add(document)
    db_session.flush()
    row.document_id = document.id
    db_session.commit()
    payload = {"analyte": "Glicemie", "value": 85}
    assert client.put(f"{API}/labs/{result_id}", headers=headers, json=payload).status_code == 409
    assert client.delete(f"{API}/labs/{result_id}", headers=headers).status_code == 409
    document.status = ProcessingStatus.DONE
    db_session.commit()
    response = client.put(f"{API}/labs/{result_id}", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["document_id"] == document.id
    assert client.delete(f"{API}/labs/{result_id}", headers=headers).status_code == 204
    assert db_session.get(Document, document.id).storage_key == "private-fictiv"


def test_explanation_has_record_citation_and_no_unbacked_clinical_cause(client):
    h = _auth_headers(client)
    rid = _add(client, h, value=120, measured_on="2026-01-10").json()["id"]
    text = client.post(f"{API}/labs/{rid}/explain", headers=h).json()["ai_explanation"]
    assert f"[L{rid}]" in text and "Mod simulat" in text
    assert "Nu există aici o sursă clinică suficientă" in text


def test_changed_or_deleted_lab_cannot_receive_stale_explanation(client, db_session):
    import pytest
    from sqlalchemy import delete, update
    from sqlalchemy.orm import Session

    from app.models.document import LabResult
    from app.services import lab_analysis

    h = _auth_headers(client)
    for action in ("update", "delete"):
        rid = _add(client, h, value=120).json()["id"]
        row = db_session.get(LabResult, rid)

        class InterleavingProvider:
            name = "external"

            def complete(self, rid=rid, action=action, **kwargs):
                with Session(db_session.get_bind()) as other:
                    statement = (update(LabResult).where(LabResult.id == rid).values(value=95)
                                 if action == "update" else
                                 delete(LabResult).where(LabResult.id == rid))
                    other.execute(statement)
                    other.commit()
                return f"Valoarea veche este 120 [L{rid}]"

        with pytest.raises(lab_analysis.LabExplanationChanged):
            lab_analysis.explain_result(db_session, InterleavingProvider(), row)
        current = db_session.get(LabResult, rid, populate_existing=True)
        if action == "update":
            assert current.value == 95 and current.ai_explanation is None
        else:
            assert current is None


def test_lab_explanation_rejects_uncited_generated_text(client, db_session):
    from app.models.document import LabResult
    from app.services import lab_analysis

    class External:
        name = "external"

        def complete(self, **kwargs):
            return "UNSUPPORTED-CLINICAL-CLAIM"

    h = _auth_headers(client)
    rid = _add(client, h, value=120).json()["id"]
    row = lab_analysis.explain_result(db_session, External(), db_session.get(LabResult, rid))
    assert "UNSUPPORTED-CLINICAL-CLAIM" not in row.ai_explanation
    assert "nu are citări verificabile" in row.ai_explanation


def test_legacy_explanation_cache_migration_preserves_original_values():
    import importlib.util
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine, text

    path = (Path(__file__).parents[1]
            / "alembic/versions/a3c5e7f9b1d2_clear_uncited_lab_explanations.py")
    spec = importlib.util.spec_from_file_location("explanation_cache_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE lab_results (id INTEGER, value FLOAT, "
                                "ai_explanation TEXT)"))
        connection.execute(text("INSERT INTO lab_results VALUES (1, 120, 'old'), (2, 90, NULL)"))
        with Operations.context(MigrationContext.configure(connection)):
            module.upgrade()
        assert connection.execute(text("SELECT * FROM lab_results ORDER BY id")).all() == [
            (1, 120, None), (2, 90, None)]
