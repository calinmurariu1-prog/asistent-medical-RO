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


def test_unrelated_question_does_not_call_provider(client, monkeypatch):
    from app.services.ai.mock import MockProvider

    def unexpected_call(*args, **kwargs):
        raise AssertionError("No relevant evidence: provider must not be called")

    monkeypatch.setattr(MockProvider, "chat", unexpected_call)
    h = _auth_headers(client)
    _add_lab(client, h)
    chat_id = _new_chat(client, h)
    message = client.post(
        f"{API}/chats/{chat_id}/messages", headers=h,
        json={"content": "Explică fractura claviculei"},
    ).json()
    assert "suficiente informații" in message["content"]
    assert message["sources"] == []


def test_invalid_or_missing_citations_are_rejected(client, monkeypatch):
    from app.services.ai.mock import MockProvider

    h = _auth_headers(client)
    _add_lab(client, h)
    chat_id = _new_chat(client, h)
    for response in ("Afirmație fără sursă", "Afirmație [S999]", "Text [S1] și [S99]"):
        monkeypatch.setattr(
            MockProvider, "chat", lambda *args, response=response, **kwargs: response
        )
        message = client.post(
            f"{API}/chats/{chat_id}/messages", headers=h,
            json={"content": "Glicemie"},
        ).json()
        assert "suficiente informații" in message["content"]
        assert message["sources"] == []


def test_only_cited_sources_are_returned(client, monkeypatch):
    from app.services.ai.mock import MockProvider

    h = _auth_headers(client)
    _add_lab(client, h)
    _add_lab(client, h)
    monkeypatch.setattr(MockProvider, "chat", lambda *args, **kwargs: "Valoare în dosar [S2].")
    message = client.post(
        f"{API}/chats/{_new_chat(client, h)}/messages", headers=h,
        json={"content": "Glicemie"},
    ).json()
    assert [source["ref"] for source in message["sources"]] == ["S2"]
    assert "NU reprezintă" in message["content"]


def test_retrieval_normalizes_romanian_diacritics():
    from app.services.rag.retriever import _tokenize

    assert _tokenize("Reacție alergică") == _tokenize("Reactie alergica")


def test_retrieval_uses_original_text_and_excludes_unverified_values(client, db_session):
    from app.models.document import Document, LabResult
    from app.services.rag import build_context

    h = _auth_headers(client)
    lab_id = _add_lab(client, h).json()["id"]
    lab = db_session.get(LabResult, lab_id)
    lab.confidence = "unverified"
    document = Document(
        patient_id=lab.patient_id, original_filename="fictiv.txt", storage_key="test-only",
        extracted_text="Glicemie: text original", ai_summary="Glicemie: rezumat inventat",
    )
    db_session.add(document)
    db_session.commit()
    retrieved = build_context(db_session, lab.patient_id, "Glicemie")
    assert "text original" in retrieved.context_text
    assert "inventat" not in retrieved.context_text
    assert [source["type"] for source in retrieved.sources] == ["document"]
    document.extracted_text = None
    db_session.commit()
    assert build_context(db_session, lab.patient_id, "Glicemie").is_empty
