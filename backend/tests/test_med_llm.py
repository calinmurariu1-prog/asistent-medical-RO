"""Tests for the MedLLM provider (micro-service is mocked)."""
from __future__ import annotations

import httpx

from app.services.ai.base import DISCLAIMER
from app.services.ai.med_llm import MedLLMProvider


class _FakeResp:
    def __init__(self, payload: dict, status: int = 200):
        self._payload = payload
        self.status_code = status
        self.text = ""

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("err", request=None, response=self)  # type: ignore[arg-type]

    def json(self) -> dict:
        return self._payload


def _provider(monkeypatch, response_text: str):
    def fake_post(url, json, timeout):  # noqa: A002
        return _FakeResp({"response": response_text})

    monkeypatch.setattr("app.services.ai.med_llm.httpx.post", fake_post)
    return MedLLMProvider(base_url="http://med-llm:3031")


def test_extract_document_parses_json(monkeypatch):
    payload = (
        '{"summary":"Rezumat.","diagnoses":["Diabet"],"treatments":[],'
        '"medications":["Metformin"],"lab_values":['
        '{"analyte":"Glicemie","value":126,"unit":"mg/dL","ref_low":70,"ref_high":99}]}'
    )
    p = _provider(monkeypatch, payload)
    result = p.extract_document("text buletin", "lab")
    assert result.summary == "Rezumat."
    assert result.diagnoses == ["Diabet"]
    assert result.medications == ["Metformin"]
    assert result.lab_values[0].analyte == "Glicemie"
    assert result.lab_values[0].value == 126


def test_extract_document_strips_markdown_fences(monkeypatch):
    payload = (
        '```json\n{"summary":"S","diagnoses":[],"treatments":[],'
        '"medications":[],"lab_values":[]}\n```'
    )
    p = _provider(monkeypatch, payload)
    assert p.extract_document("t", "lab").summary == "S"


def test_extract_document_invalid_json_falls_back(monkeypatch):
    p = _provider(monkeypatch, "not json at all")
    result = p.extract_document("t", "lab")
    assert "not json" in result.summary


def test_explain_and_chat_return_text(monkeypatch):
    p = _provider(monkeypatch, "Explicație clară.")
    expl = p.explain_lab_value(
        analyte="Glicemie", value=126, unit="mg/dL", ref_low=70, ref_high=99, flag="high"
    )
    assert expl == "Explicație clară."
    reply = p.chat(
        question="Ce e glicemia?",
        context="[S1] Glicemie 126",
        history=[("user", "salut")],
    )
    assert reply == "Explicație clară."


def test_complete_network_error_returns_disclaimer(monkeypatch):
    def boom(url, json, timeout):  # noqa: A002
        raise httpx.RequestError("connection refused")

    monkeypatch.setattr("app.services.ai.med_llm.httpx.post", boom)
    p = MedLLMProvider()
    assert p.chat(question="x", context="", history=None) == DISCLAIMER


def test_empty_response_returns_disclaimer(monkeypatch):
    p = _provider(monkeypatch, "   ")
    assert p.explain_lab_value(
        analyte="X", value=1, unit=None, ref_low=None, ref_high=None, flag="normal"
    ) == DISCLAIMER


def test_factory_selects_medllm_when_healthy(monkeypatch):
    from app.services.ai import factory

    monkeypatch.setattr(factory.settings, "AI_DEFAULT_PROVIDER", "medllm")
    monkeypatch.setattr(MedLLMProvider, "health_check", lambda self: True)
    factory.reset_medllm_health_cache()
    assert factory.get_ai_provider().__class__.__name__ == "MedLLMProvider"


def test_factory_falls_back_to_mock_when_medllm_down(monkeypatch):
    from app.services.ai import factory

    monkeypatch.setattr(factory.settings, "AI_DEFAULT_PROVIDER", "medllm")
    monkeypatch.setattr(MedLLMProvider, "health_check", lambda self: False)
    factory.reset_medllm_health_cache()
    assert factory.get_ai_provider().__class__.__name__ == "MockProvider"


def test_health_check(monkeypatch):
    class _R:
        status_code = 200

    monkeypatch.setattr("app.services.ai.med_llm.httpx.get", lambda url, timeout: _R())
    assert MedLLMProvider().health_check() is True

    def boom(url, timeout):
        raise httpx.RequestError("down")

    monkeypatch.setattr("app.services.ai.med_llm.httpx.get", boom)
    assert MedLLMProvider().health_check() is False
