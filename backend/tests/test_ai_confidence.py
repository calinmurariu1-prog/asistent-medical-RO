"""AI lab-value confidence reconciliation against the deterministic parser."""
from app.services.ai.base import ExtractedLabValue
from app.services.ai.confidence import UNVERIFIED, VERIFIED, reconcile_confidence
from app.services.ai.lab_parser import parse_lab_values


def _v(analyte: str, value: float | None) -> ExtractedLabValue:
    return ExtractedLabValue(analyte=analyte, value=value)


def test_value_confirmed_by_parser_is_verified():
    det = [ExtractedLabValue(analyte="Glicemie", value=95.0, confidence=VERIFIED)]
    vals = [_v("glicemie", 95.0)]  # different casing, same number
    reconcile_confidence(vals, det)
    assert vals[0].confidence == VERIFIED


def test_ai_only_value_is_unverified():
    det = [ExtractedLabValue(analyte="Glicemie", value=95.0, confidence=VERIFIED)]
    vals = [_v("Colesterol", 210.0)]  # parser never saw this
    reconcile_confidence(vals, det)
    assert vals[0].confidence == UNVERIFIED


def test_mismatched_number_is_unverified():
    det = [ExtractedLabValue(analyte="Glicemie", value=95.0, confidence=VERIFIED)]
    vals = [_v("Glicemie", 120.0)]  # AI mis-read the number
    reconcile_confidence(vals, det)
    assert vals[0].confidence == UNVERIFIED


def test_missing_number_is_unverified():
    vals = [_v("Glicemie", None)]
    reconcile_confidence(vals, [])
    assert vals[0].confidence == UNVERIFIED


def test_parser_output_is_verified_by_default():
    text = "Glicemie 95 mg/dL 70 - 110\nColesterol 210 mg/dL 0 - 200"
    parsed = parse_lab_values(text)
    assert parsed and all(p.confidence == VERIFIED for p in parsed)
