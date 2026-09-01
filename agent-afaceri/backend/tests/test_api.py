"""Teste API (TestClient, provider mock offline)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_skills():
    r = client.get("/skills")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 6
    assert {s["category"] for s in data} == {"juridic", "business"}


def test_run_skill_missing_input():
    r = client.post("/skills/company_setup/run", json={"inputs": {"form": "SRL"}})
    assert r.status_code == 422  # lipsește "activity"


def test_run_skill_ok():
    r = client.post(
        "/skills/company_setup/run",
        json={"inputs": {"form": "SRL", "activity": "comerț online"}},
    )
    assert r.status_code == 200
    assert "SRL" in r.json()["result"]


def test_chat():
    r = client.post("/chat", json={"message": "Cum înființez un SRL?", "domain": "business"})
    assert r.status_code == 200
    assert r.json()["reply"]
