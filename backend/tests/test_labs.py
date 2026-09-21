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
