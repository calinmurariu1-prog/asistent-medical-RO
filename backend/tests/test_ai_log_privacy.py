"""Provider failures must not copy request content or keys into app logs."""
import httpx

from app.services.ai.base import DISCLAIMER
from app.services.ai.llm import LLMProvider
from app.services.ai.med_llm import MedLLMProvider
from app.services.places.google import GooglePlacesProvider

SENSITIVE = "synthetic-patient-address-and-secret-key"


def test_llm_errors_log_only_exception_type(monkeypatch, caplog):
    provider = LLMProvider()

    def fail(*args, **kwargs):
        raise RuntimeError(SENSITIVE)

    monkeypatch.setattr(provider, "_complete", fail)
    assert provider.complete(system="test", user="test") == DISCLAIMER
    provider.extract_document("test", "lab")
    provider.explain_lab_value(analyte="Test", value=1, unit=None,
                               ref_low=None, ref_high=None, flag="unknown")
    provider.chat(question="test", context="test")
    assert "RuntimeError" in caplog.text
    assert SENSITIVE not in caplog.text


def test_medllm_error_response_is_not_logged(monkeypatch, caplog):
    response = httpx.Response(500, text=SENSITIVE,
                             request=httpx.Request("POST", "https://example.test/complete"))
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: response)
    assert MedLLMProvider().complete(system="test", user="test") == DISCLAIMER
    assert "500" in caplog.text
    assert SENSITIVE not in caplog.text


def test_geocoding_does_not_log_address_or_exception_content(monkeypatch, caplog):
    def fail(*args, **kwargs):
        raise RuntimeError(SENSITIVE)

    monkeypatch.setattr(httpx, "get", fail)
    assert GooglePlacesProvider().geocode(SENSITIVE) is None
    assert SENSITIVE not in caplog.text


def test_malformed_pdf_diagnostics_do_not_log_original_bytes(monkeypatch, caplog):
    from app.services.ocr import _extract_pdf

    def no_ocr(*args, **kwargs):
        raise RuntimeError(SENSITIVE)

    monkeypatch.setattr("pdf2image.convert_from_bytes", no_ocr)
    assert _extract_pdf(SENSITIVE.encode()) == ""
    assert SENSITIVE not in caplog.text
    assert "synthe" not in caplog.text
    assert "PDF text extraction failed" in caplog.text
