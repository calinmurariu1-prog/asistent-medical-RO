"""Normalize spelling only. Never perform clinical unit conversions."""

_CANONICAL = {
    "mg/dl": "mg/dL", "g/dl": "g/dL", "mg/l": "mg/L", "g/l": "g/L",
    "mmol/l": "mmol/L", "µmol/l": "µmol/L", "umol/l": "µmol/L",
    "µg/l": "µg/L", "ug/l": "µg/L", "µg/dl": "µg/dL", "ug/dl": "µg/dL",
}


def normalize_unit(unit: str | None) -> str | None:
    if not unit or not unit.strip():
        return None
    cleaned = unit.strip().replace("μ", "µ")
    return _CANONICAL.get(cleaned.lower(), cleaned)
