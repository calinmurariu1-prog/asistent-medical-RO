"""Offline provider: deterministic extraction with no external API call.

Used automatically when no AI API key is configured (and in tests), so the
document pipeline is fully functional without network access.
"""
from __future__ import annotations

import re

from app.services.ai.base import DISCLAIMER, DocumentExtraction
from app.services.ai.lab_parser import parse_lab_values
from app.services.ai.lab_reference import lookup

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

    def explain_lab_value(
        self,
        *,
        analyte: str,
        value: float | None,
        unit: str | None,
        ref_low: float | None,
        ref_high: float | None,
        flag: str,
        trend: str | None = None,
    ) -> str:
        info = lookup(analyte)
        unit_str = f" {unit}" if unit else ""
        parts: list[str] = []

        if info:
            parts.append(f"{info.label}: {info.about}")

        if value is not None:
            ref = ""
            if ref_low is not None and ref_high is not None:
                ref = f" (interval de referință {ref_low}–{ref_high}{unit_str})"
            parts.append(f"Valoarea ta este {value}{unit_str}{ref}.")

        status_text = {
            "unknown": ("Nu pot evalua încadrarea: lipsește o valoare numerică sau un interval "
                        "de referință valid. Verifică documentul original împreună cu medicul."),
            "high": "Valoarea este peste intervalul de referință.",
            "critical_high": "Valoarea este mult peste intervalul de referință.",
            "low": "Valoarea este sub intervalul de referință.",
            "critical_low": "Valoarea este mult sub intervalul de referință.",
            "normal": "Valoarea se încadrează în intervalul de referință.",
        }.get(flag, "")
        if status_text:
            parts.append(status_text)

        if info and flag in ("high", "critical_high"):
            parts.append(info.high_meaning)
        elif info and flag in ("low", "critical_low"):
            parts.append(info.low_meaning)

        if trend:
            parts.append(f"Evoluție față de măsurătorile anterioare: {trend}.")

        parts.append(DISCLAIMER)
        return " ".join(parts)

    def complete(self, *, system: str, user: str) -> str:
        # Rarely used: the skills framework prefers each skill's own mock output.
        return f"(răspuns simulat) {DISCLAIMER}"

    def chat(
        self,
        *,
        question: str,
        context: str,
        history: list[tuple[str, str]] | None = None,
    ) -> str:
        if not context.strip():
            return (
                "Nu am suficiente informații în dosarul tău medical pentru a "
                "răspunde la această întrebare. Îți recomand să încarci "
                f"documentele relevante sau să discuți cu medicul. {DISCLAIMER}"
            )
        # Deterministic, grounded summary of the retrieved snippets.
        top = [ln for ln in context.splitlines() if ln.strip()][:3]
        joined = " ".join(top)
        return (
            "Pe baza informațiilor din dosarul tău medical, iată ce este "
            f"relevant pentru întrebarea ta: {joined} "
            "Sursele sunt indicate prin marcaje [S#]. "
            f"{DISCLAIMER}"
        )
