"""Offline provider: deterministic extraction with no external API call.

Used automatically when no AI API key is configured (and in tests), so the
document pipeline is fully functional without network access.
"""
from __future__ import annotations

import re

from app.services.ai.base import DocumentExtraction
from app.services.ai.lab_parser import parse_lab_values

_DIAG_RE = re.compile(r"(?:diagnostic|diagnoza)[:\s]+(.+)", re.IGNORECASE)
_TREAT_RE = re.compile(r"(?:tratament|recomand[ăa]ri)[:\s]+(.+)", re.IGNORECASE)
_MED_RE = re.compile(
    r"\b([A-ZĂÂÎȘȚ][a-zăâîșț]+(?:in|ol|il|am|ax|ină|ide))\b"
)


class MockProvider:
    name = "mock"

    def extract_document(self, text: str, category: str) -> DocumentExtraction:
        lab_values = parse_lab_values(text)

        diagnoses = [m.group(1).strip() for m in _DIAG_RE.finditer(text)]
        treatments = [m.group(1).strip() for m in _TREAT_RE.finditer(text)]
        medications = sorted({m.group(1) for m in _MED_RE.finditer(text)})[:10]

        parts = []
        if lab_values:
            parts.append(f"{len(lab_values)} parametri de laborator identificați.")
        if diagnoses:
            parts.append(f"Diagnostice menționate: {', '.join(diagnoses)}.")
        if treatments:
            parts.append(f"Tratamente/recomandări: {', '.join(treatments)}.")
        summary = " ".join(parts) or (
            "Document procesat. Nu s-au putut extrage automat date structurate; "
            "textul este disponibil pentru consultare."
        )

        return DocumentExtraction(
            summary=summary,
            diagnoses=diagnoses,
            treatments=treatments,
            medications=medications,
            lab_values=lab_values,
        )
