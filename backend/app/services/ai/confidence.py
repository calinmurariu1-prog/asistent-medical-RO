"""Check AI-extracted lab fields against deterministic extraction.

Agreement covers analyte, numeric value, spelling-normalized unit and reference
bounds. Verification describes extraction agreement, not clinical validation.
"""
from __future__ import annotations

import math
import re

from app.services.ai.base import ExtractedLabValue
from app.services.ai.lab_units import normalize_unit

VERIFIED = "verified"
UNVERIFIED = "unverified"


def _norm(analyte: str) -> str:
    """Loose analyte key: lowercase, strip diacritics/punctuation/spaces."""
    s = analyte.lower().strip()
    for a, b in (("ă", "a"), ("â", "a"), ("î", "i"), ("ș", "s"), ("ț", "t")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]", "", s)


def _same_number(left: float | None, right: float | None) -> bool:
    if left is None or right is None:
        return left is right
    return math.isfinite(left) and math.isfinite(right) and math.isclose(
        left, right, rel_tol=1e-9, abs_tol=1e-12
    )


def reconcile_confidence(
    values: list[ExtractedLabValue], deterministic: list[ExtractedLabValue]
) -> None:
    """Require agreement on analyte, value, unit and both reference bounds."""
    for value in values:
        value.unit = normalize_unit(value.unit)
        matches = any(
            source.confidence == VERIFIED and value.value is not None
            and _norm(value.analyte) == _norm(source.analyte)
            and normalize_unit(value.unit) == normalize_unit(source.unit)
            and _same_number(value.value, source.value)
            and _same_number(value.ref_low, source.ref_low)
            and _same_number(value.ref_high, source.ref_high)
            for source in deterministic
        )
        value.confidence = VERIFIED if matches else UNVERIFIED
