"""Tests for Module 11 - Medical AI chat with RAG (mock provider)."""
from __future__ import annotations

API = "/api/v1"


def _auth_headers(client, email="chat@example.com"):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    tokens = client.post(
        f"{API}/auth/login", json={"email": email, "password": "Parola1234"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _new_chat(client, h):
    return client.post(f"{API}/chats", headers=h, json={}).json()["id"]


def _add_lab(client, h):
    return client.post(
        f"{API}/labs",
        headers=h,
        json={
            "analyte": "Glicemie",
            "value": 130,
            "unit": "mg/dL",
            "ref_low": 70,
            "ref_high": 99,
            "measured_on": "2026-01-10",
        },
    )


def test_create_list_and_get_chat(client):
    h = _auth_headers(client)
    chat_id = _new_chat(client, h)
    assert len(client.get(f"{API}/chats", headers=h).json()) == 1
    body = client.get(f"{API}/chats/{chat_id}", headers=h).json()
    assert body["id"] == chat_id
    assert body["messages"] == []


def test_answer_without_data_says_insufficient(client):
    h = _auth_headers(client)
    chat_id = _new_chat(client, h)
    r = client.post(
        f"{API}/chats/{chat_id}/messages",
        headers=h,
        json={"content": "Cum stau cu glicemia?"},
    )
    assert r.status_code == 200, r.text
    msg = r.json()
    assert msg["role"] == "assistant"
    assert "suficiente informații" in msg["content"].lower()
    assert msg["sources"] == []
    assert "NU reprezintă" in msg["content"]  # disclaimer wording


def test_answer_is_grounded_in_record(client):
    h = _auth_headers(client)
    _add_lab(client, h)
    chat_id = _new_chat(client, h)
    r = client.post(
        f"{API}/chats/{chat_id}/messages",
        headers=h,
        json={"content": "Ce arată analiza mea de Glicemie?"},
    )
    assert r.status_code == 200, r.text
    msg = r.json()
    assert "Glicemie" in msg["content"]
    # Sources cite the lab result used for grounding.
    assert any(s["type"] == "lab_result" for s in msg["sources"])
    assert "orientativ" in msg["content"].lower()  # disclaimer


def test_conversation_persists_history(client):
    h = _auth_headers(client)
    _add_lab(client, h)
    chat_id = _new_chat(client, h)
    for q in ("Ce e glicemia?", "Dar valoarea mea?"):
        assert (
            client.post(
                f"{API}/chats/{chat_id}/messages", headers=h, json={"content": q}
            ).status_code
            == 200
        )
    detail = client.get(f"{API}/chats/{chat_id}", headers=h).json()
    # 2 user + 2 assistant messages, ordered.
    roles = [m["role"] for m in detail["messages"]]
    assert roles == ["user", "assistant", "user", "assistant"]
    # Title auto-set from the first question.
    assert detail["title"].startswith("Ce e glicemia")


def test_chat_isolated_per_patient(client):
    h1 = _auth_headers(client, "c1@example.com")
    h2 = _auth_headers(client, "c2@example.com")
    chat_id = _new_chat(client, h1)
    assert client.get(f"{API}/chats/{chat_id}", headers=h2).status_code == 404
    assert (
        client.post(
            f"{API}/chats/{chat_id}/messages", headers=h2, json={"content": "x"}
        ).status_code
        == 404
    )


def test_delete_chat(client):
    h = _auth_headers(client)
    chat_id = _new_chat(client, h)
    assert client.delete(f"{API}/chats/{chat_id}", headers=h).status_code == 204
    assert client.get(f"{API}/chats/{chat_id}", headers=h).status_code == 404
