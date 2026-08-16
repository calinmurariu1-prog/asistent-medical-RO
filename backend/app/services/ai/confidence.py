"""Cross-check AI-extracted lab values against the deterministic parser.

An LLM (Gemini Flash) can invent or mis-read numbers. The regex-based
`parse_lab_values` reads the exact document text, so wherever it independently
finds the same number we treat the value as *verified*. Everything else is left
*unverified* and shown to the user as "de confirmat".
"""
from __future__ import annotations

import re

from app.services.ai.base import ExtractedLabValue

VERIFIED = "verified"
UNVERIFIED = "unverified"


def _norm(analyte: str) -> str:
    """Loose analyte key: lowercase, strip diacritics/punctuation/spaces."""
    s = analyte.lower().strip()
    for a, b in (("ă", "a"), ("â", "a"), ("î", "i"), ("ș", "s"), ("ț", "t")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]", "", s)


def _matches(value: float, candidates: list[float]) -> bool:
    # Agree within 0.5% (or a tiny absolute epsilon for values near zero).
    return any(abs(value - c) <= max(0.01, abs(c) * 0.005) for c in candidates)


def reconcile_confidence(
    values: list[ExtractedLabValue], deterministic: list[ExtractedLabValue]
) -> None:
    """Set `confidence` on each value in place, using `deterministic` as truth."""
    index: dict[str, list[float]] = {}
    for d in deterministic:
        if d.value is not None:
            index.setdefault(_norm(d.analyte), []).append(d.value)

    for v in values:
        if v.confidence == VERIFIED:
            continue  # already trusted (e.g. came straight from the parser)
        if v.value is not None and _matches(v.value, index.get(_norm(v.analyte), [])):
            v.confidence = VERIFIED
        else:
            v.confidence = UNVERIFIED
