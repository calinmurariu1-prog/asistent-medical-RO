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


def test_unit_reference_or_small_numeric_mismatch_is_not_verified():
    from dataclasses import replace

    source = ExtractedLabValue(analyte="Glicemie", value=95, unit="mg/dL",
                               ref_low=70, ref_high=99, confidence=VERIFIED)
    for changes in ({"unit":"mmol/L"}, {"ref_high":100}, {"ref_low":None}, {"value":95.001}):
        value = replace(source, **changes)
        reconcile_confidence([value], [source])
        assert value.confidence == UNVERIFIED


def test_unit_spelling_normalization_does_not_convert_measurements():
    source = ExtractedLabValue(analyte="Test", value=95, unit="μg/L", confidence=VERIFIED)
    value = ExtractedLabValue(analyte="Test", value=95, unit="ug/l")
    reconcile_confidence([value], [source])
    assert value.confidence == VERIFIED
    assert value.unit == "µg/L"
    assert value.value == 95


def test_ambiguous_thousands_separator_requires_confirmation():
    for number in ("1.234", "1,234", "12.345"):
        parsed = parse_lab_values(f"Glicemie {number} mg/dL 70 - 99")[0]
        assert parsed.value is None
        assert parsed.value_text == number
        assert parsed.confidence == UNVERIFIED
    parsed = parse_lab_values("TSH 0,270 uUI/mL 0,1 - 4,2")[0]
    assert parsed.value == 0.27
    assert parsed.confidence == VERIFIED


def test_ambiguous_reference_cannot_verify_an_ai_guess():
    parsed = parse_lab_values("Test 2 mg/L 1.000 - 3.000")
    value = ExtractedLabValue(analyte="Test", value=2, unit="mg/L", ref_low=1, ref_high=3)
    reconcile_confidence([value], parsed)
    assert value.confidence == UNVERIFIED


def test_reference_without_unit_is_not_split_into_a_numeric_unit():
    parsed = parse_lab_values("Glicemie 95 70 - 99")[0]
    assert parsed.unit is None
    assert parsed.value == 95
    assert parsed.ref_low == 70
    assert parsed.ref_high == 99


def test_parser_requires_boundaries_between_numbers_and_reference():
    assert parse_lab_values("Glicemie 9570-99") == []
    assert parse_lab_values("Glicemie 95 mg/dL70-99") == []
    parsed = parse_lab_values("Glicemie 95mg/dL(70-99)")[0]
    assert parsed.unit == "mg/dL"
    assert parsed.ref_low == 70
