"""Heuristic parser that pulls lab analyte/value/unit/reference from free text.

Used by the offline mock provider and as a deterministic pre-pass before the
LLM. Handles common Romanian lab-report layouts, e.g.:

    Glicemie 105 mg/dL (70 - 99)
    Hemoglobina: 13.5 g/dL  12 - 16
    TSH 4.80 uUI/mL  [0.27-4.20]
"""
from __future__ import annotations

import re

from app.services.ai.base import ExtractedLabValue
from app.services.ai.lab_units import normalize_unit

_NUM = r"[-+]?\d+(?:[.,]\d+)?"
_UNIT = r"(?:10\^\d{1,2}/[A-Za-zµμ]+|[A-Za-zµμ%][A-Za-zµμ%/\^\d]*)"

# analyte  value  [unit]  ref_low - ref_high (with optional brackets/paren)
_LINE_RE = re.compile(
    rf"""^\s*
    (?P<analyte>[A-Za-zĂÂÎȘȚăâîșț][A-Za-zĂÂÎȘȚăâîșț0-9 .\-()]{{1,60}}?)   # name
    [:\s]\s*
    (?P<value>{_NUM})
    (?:\s*(?P<unit>{_UNIT})(?=\s|[\[(]))?
    (?:\s+|(?=[\[(]))[\[(]?\s*
    (?P<low>{_NUM})\s*[-–]\s*(?P<high>{_NUM})
    \s*[\])]?
    \s*$""",
    re.VERBOSE,
)


def _to_float(raw: str | None) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return None


def parse_lab_values(text: str) -> list[ExtractedLabValue]:
    results: list[ExtractedLabValue] = []
    for line in text.splitlines():
        m = _LINE_RE.match(line)
        if not m:
            continue
        analyte = m.group("analyte").strip(" .:-")
        if len(analyte) < 2:
            continue
        # A single separator followed by three digits can mean decimals or
        # thousands. Retain its original spelling for review instead of guessing.
        raw_numbers = [m.group(key) for key in ("value", "low", "high")]
        ambiguous = any(re.fullmatch(r"[-+]?[1-9]\d*[.,]\d{3}", raw) for raw in raw_numbers)
        results.append(
            ExtractedLabValue(
                analyte=analyte,
                value=None if ambiguous else _to_float(m.group("value")),
                value_text=m.group("value"),
                unit=normalize_unit(m.group("unit")),
                ref_low=None if ambiguous else _to_float(m.group("low")),
                ref_high=None if ambiguous else _to_float(m.group("high")),
                # Technical extraction agreement is not clinical validation.
                confidence="unverified" if ambiguous else "verified",
            )
        )
    return results
