"""No external AI calls without provider-specific, revocable consent."""
from app.core.config import settings
from app.main import app
from app.services.ai import get_ai_provider
from app.services.ai.mock import MockProvider

API = "/api/v1"


def auth(client, email="consent-scope@example.com"):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    tokens = client.post(f"{API}/auth/login", json={
        "email": email, "password": "Parola1234"}).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


class ExternalSpy(MockProvider):
    name = "openai"

    def __init__(self):
        self.calls = 0

    def complete(self, **kwargs):
        self.calls += 1
        return "Test simulat, fără apel extern."

    def extract_document(self, *args, **kwargs):
        self.calls += 1
        return super().extract_document(*args, **kwargs)

    def explain_lab_value(self, **kwargs):
        self.calls += 1
        return super().explain_lab_value(**kwargs)

    def chat(self, **kwargs):
        self.calls += 1
        return "Test simulat, fără apel extern."


def test_all_external_entrypoints_require_consent_even_with_flag_off(client, monkeypatch, storage):
    monkeypatch.setattr(settings, "REQUIRE_AI_CONSENT", False)
    h = auth(client)
    provider = ExternalSpy()
    from app.api.routes import ai_skills

    monkeypatch.setattr(ai_skills, "get_ai_provider", lambda: provider)
    app.dependency_overrides[get_ai_provider] = lambda: provider
    try:
        endpoints = [
            ("/labs/1/explain", {}), ("/labs/explain-all", {}),
            ("/documents/1/reprocess", {}), ("/ai/summarize-record", {}),
            ("/ai/compare-analyte", {"analyte": "Glicemie"}),
            ("/ai/skills/explain_medication", {"inputs": {"name": "Test"}}),
            ("/chats/1/messages", {"content": "Test"}),
        ]
        for endpoint, payload in endpoints:
            assert client.post(API + endpoint, headers=h, json=payload).status_code == 403
        assert client.post(f"{API}/documents", headers=h,
                           files={"file": ("test.pdf", b"test", "application/pdf")}
                           ).status_code == 403
        assert not storage._objects
        assert provider.calls == 0
        state = client.get(f"{API}/ai/status", headers=h).json()
        assert state == {"provider": "openai", "simulated": False, "consent_required": True}
    finally:
        app.dependency_overrides.pop(get_ai_provider)


def test_grant_revoke_and_provider_change(client, monkeypatch):
    monkeypatch.setattr(settings, "REQUIRE_AI_CONSENT", False)
    h = auth(client)
    other = auth(client, "other-consent@example.com")
    client.post(f"{API}/medications", headers=h, json={"name": "Tratament fictiv"})
    provider = ExternalSpy()
    app.dependency_overrides[get_ai_provider] = lambda: provider
    try:
        grant = {"consent_type": "ai_processing", "granted": True, "provider": "openai"}
        assert client.post(f"{API}/gdpr/consents", headers=h, json=grant).status_code == 201
        assert client.post(f"{API}/ai/summarize-record", headers=h).status_code == 200
        assert provider.calls == 1
        assert client.post(f"{API}/ai/summarize-record", headers=other).status_code == 403
        provider.name = "anthropic"
        assert client.post(f"{API}/ai/summarize-record", headers=h).status_code == 403
        assert client.post(f"{API}/gdpr/consents", headers=h, json=grant).status_code == 409
        provider.name = "openai"
        client.post(f"{API}/gdpr/consents", headers=h,
                    json={"consent_type": "ai_processing", "granted": False})
        assert client.post(f"{API}/ai/summarize-record", headers=h).status_code == 403
        assert provider.calls == 1
    finally:
        app.dependency_overrides.pop(get_ai_provider)


def test_legacy_generic_consent_does_not_authorize_external_provider(client, db_session):
    from sqlalchemy import select

    from app.models.enums import ConsentType
    from app.models.user import Consent, User

    h = auth(client)
    user = db_session.scalar(select(User).where(User.email == "consent-scope@example.com"))
    db_session.add(Consent(user_id=user.id, consent_type=ConsentType.AI_PROCESSING,
                           granted=True, version="1.0"))
    db_session.commit()
    provider = ExternalSpy()
    app.dependency_overrides[get_ai_provider] = lambda: provider
    try:
        assert client.post(f"{API}/ai/summarize-record", headers=h).status_code == 403
        assert provider.calls == 0
    finally:
        app.dependency_overrides.pop(get_ai_provider)
