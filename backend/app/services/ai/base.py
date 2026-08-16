"""Shared AI types and the provider interface."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

# Appended to every AI explanation/recommendation shown to the user.
DISCLAIMER = (
    "Aceste informații sunt orientative, generate automat, și NU reprezintă "
    "un diagnostic. Consultați întotdeauna medicul."
)


@dataclass
class ExtractedLabValue:
    analyte: str
    value: float | None = None
    value_text: str | None = None
    unit: str | None = None
    ref_low: float | None = None
    ref_high: float | None = None
    # "verified"   -> confirmed by the deterministic parser reading the raw text
    # "unverified" -> produced by the LLM only; surfaced to the user as
    #                 "de confirmat" so an AI-invented number is never trusted.
    confidence: str = "unverified"


@dataclass
class DocumentExtraction:
    """Structured result of analysing a medical document (Module 4)."""

    summary: str = ""
    diagnoses: list[str] = field(default_factory=list)
    treatments: list[str] = field(default_factory=list)
    medications: list[str] = field(default_factory=list)
    lab_values: list[ExtractedLabValue] = field(default_factory=list)

    def to_metadata(self) -> dict:
        return {
            "diagnoses": self.diagnoses,
            "treatments": self.treatments,
            "medications": self.medications,
            "lab_values": [v.__dict__ for v in self.lab_values],
        }


class AIProvider(Protocol):
    """Interface every concrete provider (and the mock) implements."""

    name: str

    def extract_document(self, text: str, category: str) -> DocumentExtraction:
        """Extract diagnoses, treatments, medications, lab values and a summary."""
        ...

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
        """Return a short, patient-friendly explanation of one lab value."""
        ...

    def chat(
        self,
        *,
        question: str,
        context: str,
        history: list[tuple[str, str]] | None = None,
    ) -> str:
        """Answer a question grounded ONLY in the provided patient context.

        Must refuse to invent information: if the context is insufficient, say
        so plainly. `history` is prior (role, content) turns for continuity.
        """
        ...

    def complete(self, *, system: str, user: str) -> str:
        """Generic text completion used by the AI-skills framework."""
        ...
