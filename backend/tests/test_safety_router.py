from __future__ import annotations

import pytest

from app.services.ai.safety_router import emergency_reply


@pytest.mark.parametrize(
    "message",
    [
        "Nu pot respira",
        "Nu mai pot să respir!",
        "Tata nu respira",
        "Mă sufoc",
        "Am o durere puternică în piept",
        "Mă doare pieptul",
        "Gura mi s-a strâmbat",
        "Brusc nu poate vorbi",
        "Cred că am un infarct",
        "Este inconștient",
    ],
)
def test_emergency_signals_are_local_and_non_diagnostic(message):
    reply = emergency_reply(message)
    assert reply is not None
    assert "112" in reply
    assert "fără analiză AI" in reply
    assert "Nu pot stabili cauza" in reply


@pytest.mark.parametrize(
    "message", ["Ce este glicemia?", "Ce este un infarct?", "Analizele mele", ""]
)
def test_other_questions_are_not_classified_as_safe(message):
    assert emergency_reply(message) is None


def test_emergency_chat_bypasses_external_consent_and_model(client, monkeypatch):
    from app.core.config import settings
    from app.services.ai.mock import MockProvider

    monkeypatch.setattr(settings, "REQUIRE_AI_CONSENT", True)

    def unexpected(*args, **kwargs):
        raise AssertionError("Emergency message must not reach the provider")

    monkeypatch.setattr(MockProvider, "chat", unexpected)
    client.post(
        "/api/v1/auth/register",
        json={"email": "emergency@example.com", "password": "Testing-pass-123!"},
    )
    tokens = client.post(
        "/api/v1/auth/login",
        json={"email": "emergency@example.com", "password": "Testing-pass-123!"},
    ).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    chat_id = client.post("/api/v1/chats", headers=headers, json={}).json()["id"]
    endpoint = f"/api/v1/chats/{chat_id}/messages"
    response = client.post(endpoint, headers=headers, json={"content": "Nu pot respira"})
    assert response.status_code == 200
    assert "112" in response.json()["content"]
    assert {source["ref"] for source in response.json()["sources"]} == {"E1", "E2", "E3"}
    assert (
        client.post(endpoint, headers=headers, json={"content": "Explică glicemia"}).status_code
        == 403
    )
    assert len(client.get(f"/api/v1/chats/{chat_id}", headers=headers).json()["messages"]) == 2
