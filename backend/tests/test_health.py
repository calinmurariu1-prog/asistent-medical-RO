"""Tests for the health-data import module (Apple / Google / Huawei)."""
from __future__ import annotations

import io
import json
import zipfile

API = "/api/v1"


def _auth(client, email="health@example.com"):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    tokens = client.post(
        f"{API}/auth/login", json={"email": email, "password": "Parola1234"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


APPLE_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="ro_RO">
  <Record type="HKQuantityTypeIdentifierStepCount" unit="count" value="523"
          startDate="2024-01-01 08:00:00 +0000" endDate="2024-01-01 09:00:00 +0000"/>
  <Record type="HKQuantityTypeIdentifierHeartRate" unit="count/min" value="72"
          startDate="2024-01-01 08:05:00 +0000" endDate="2024-01-01 08:05:00 +0000"/>
  <Record type="HKQuantityTypeIdentifierBodyMass" unit="kg" value="74.5"
          startDate="2024-01-01 07:00:00 +0000" endDate="2024-01-01 07:00:00 +0000"/>
  <Record type="HKQuantityTypeIdentifierOxygenSaturation" unit="%" value="0.98"
          startDate="2024-01-01 07:30:00 +0000" endDate="2024-01-01 07:30:00 +0000"/>
  <Record type="HKCategoryTypeIdentifierSleepAnalysis"
          value="HKCategoryValueSleepAnalysisAsleepCore"
          startDate="2024-01-01 00:00:00 +0000" endDate="2024-01-01 06:00:00 +0000"/>
</HealthData>
"""


def test_import_apple_xml(client):
    h = _auth(client)
    r = client.post(
        f"{API}/health-data/import/apple_health",
        headers=h,
        files={"file": ("export.xml", APPLE_XML, "application/xml")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["imported"] == 5
    assert body["metrics"]["steps"] == 1
    assert body["metrics"]["sleep"] == 1

    summary = client.get(f"{API}/health-data/summary", headers=h).json()
    assert summary["total_samples"] == 5
    spo2 = next(m for m in summary["metrics"] if m["metric_type"] == "oxygen_saturation")
    assert spo2["latest_value"] == 98.0  # fraction 0.98 -> 98 %
    sleep = next(m for m in summary["metrics"] if m["metric_type"] == "sleep")
    assert sleep["latest_value"] == 360.0  # 6h -> 360 min


def test_import_apple_zip_and_idempotent(client):
    h = _auth(client)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("apple_health_export/export.xml", APPLE_XML)
    payload = buf.getvalue()

    first = client.post(
        f"{API}/health-data/import/apple_health",
        headers=h,
        files={"file": ("export.zip", payload, "application/zip")},
    ).json()
    assert first["imported"] == 5

    # Re-importing the same data inserts nothing new.
    second = client.post(
        f"{API}/health-data/import/apple_health",
        headers=h,
        files={"file": ("export.zip", payload, "application/zip")},
    ).json()
    assert second["imported"] == 0
    assert second["duplicates"] == 5


def test_import_google_fit_json(client):
    h = _auth(client)
    payload = {
        "Data Points": [
            {
                "dataTypeName": "com.google.step_count.delta",
                "startTimeNanos": "1704096000000000000",
                "fitValue": [{"value": {"intVal": 1200}}],
            },
            {
                "dataTypeName": "com.google.weight",
                "startTimeNanos": "1704096000000000000",
                "fitValue": [{"value": {"fpVal": 73.2}}],
            },
        ]
    }
    r = client.post(
        f"{API}/health-data/import/google_health",
        headers=h,
        files={"file": ("fit.json", json.dumps(payload).encode(), "application/json")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["imported"] == 2


def test_import_generic_json_huawei(client):
    h = _auth(client)
    payload = {
        "samples": [
            {"type": "steps", "value": 900, "unit": "count", "recorded_at": "2024-02-01T08:00:00Z"},
            {"type": "spo2", "value": 96, "recorded_at": "2024-02-01T08:10:00Z"},
        ]
    }
    r = client.post(
        f"{API}/health-data/import/huawei_health",
        headers=h,
        files={"file": ("huawei.json", json.dumps(payload).encode(), "application/json")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["imported"] == 2


def test_sources_and_sample_and_series(client):
    h = _auth(client)
    sources = client.get(f"{API}/health-data/sources", headers=h).json()
    assert {s["source"] for s in sources} == {
        "apple_health",
        "google_health",
        "huawei_health",
    }
    assert all(not s["connected"] for s in sources)

    client.post(f"{API}/health-data/import-sample", headers=h)
    steps = client.get(f"{API}/health-data/metrics/steps", headers=h).json()
    assert len(steps) == 7  # one per day
    assert steps[0]["unit"] == "count"


def test_import_invalid_json_rejected(client):
    h = _auth(client)
    r = client.post(
        f"{API}/health-data/import/google_health",
        headers=h,
        files={"file": ("bad.json", b"not json", "application/json")},
    )
    assert r.status_code == 422


def test_delete_source(client):
    h = _auth(client)
    client.post(
        f"{API}/health-data/import/apple_health",
        headers=h,
        files={"file": ("export.xml", APPLE_XML, "application/xml")},
    )
    assert client.get(f"{API}/health-data/summary", headers=h).json()["total_samples"] == 5
    assert client.delete(f"{API}/health-data/apple_health", headers=h).status_code == 204
    assert client.get(f"{API}/health-data/summary", headers=h).json()["total_samples"] == 0
