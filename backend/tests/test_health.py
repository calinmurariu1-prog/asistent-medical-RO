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


def test_import_json_native_sync(client):
    h = _auth(client, email="native@example.com")
    payload = {
        "samples": [
            {"type": "steps", "value": 8210, "unit": "count", "recorded_at": "2024-03-01T07:00:00Z"},  # noqa: E501
            {"type": "heart_rate", "value": 64, "recorded_at": "2024-03-01T07:05:00Z"},
            {"type": "oxygen_saturation", "value": 98, "recorded_at": "2024-03-01T07:06:00Z"},  # noqa: E501
        ]
    }
    r = client.post(
        f"{API}/health-data/import-json/apple_health", headers=h, json=payload
    )
    assert r.status_code == 200, r.text
    assert r.json()["imported"] == 3

    # Idempotent: same payload again inserts nothing.
    again = client.post(
        f"{API}/health-data/import-json/apple_health", headers=h, json=payload
    ).json()
    assert again["imported"] == 0
    assert again["duplicates"] == 3

    summary = client.get(f"{API}/health-data/summary", headers=h).json()
    assert summary["total_samples"] == 3
    assert "apple_health" in summary["connected_sources"]


def test_native_sync_detects_wearable(client):
    h = _auth(client, email="watch@example.com")
    payload = {
        "samples": [
            {"type": "steps", "value": 5000, "recorded_at": "2024-04-01T07:00:00Z"},
            {"type": "heart_rate", "value": 61, "recorded_at": "2024-04-01T07:01:00Z"},
        ],
        "devices": [
            {"name": "Apple Watch Series 9", "metrics": ["steps", "heart_rate"]},
        ],
    }
    r = client.post(
        f"{API}/health-data/import-json/apple_health", headers=h, json=payload
    )
    assert r.status_code == 200, r.text

    devices = client.get(f"{API}/health-data/devices", headers=h).json()
    assert len(devices) == 1
    dev = devices[0]
    assert dev["name"] == "Apple Watch Series 9"
    assert dev["vendor"] == "Apple"  # inferred server-side
    assert set(dev["metrics"]) == {"steps", "heart_rate"}
    assert dev["source"] == "apple_health"

    # Re-sync merges metrics and updates last_seen (no duplicate device).
    payload["devices"][0]["metrics"] = ["sleep"]
    payload["samples"] = [
        {"type": "sleep", "value": 400, "recorded_at": "2024-04-02T07:00:00Z"}
    ]
    client.post(f"{API}/health-data/import-json/apple_health", headers=h, json=payload)
    devices = client.get(f"{API}/health-data/devices", headers=h).json()
    assert len(devices) == 1
    assert set(devices[0]["metrics"]) == {"steps", "heart_rate", "sleep"}


def test_import_json_rejects_manual_source(client):
    h = _auth(client, email="native2@example.com")
    r = client.post(
        f"{API}/health-data/import-json/manual",
        headers=h,
        json={"samples": [{"type": "steps", "value": 1, "recorded_at": "2024-03-01T07:00:00Z"}]},
    )
    assert r.status_code == 400


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
