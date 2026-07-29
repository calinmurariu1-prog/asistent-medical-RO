"""Shared AI types and the provider interface."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ExtractedLabValue:
    analyte: str
    value: float | None = None
    value_text: str | None = None
    unit: str | None = None
    ref_low: float | None = None
    ref_high: float | None = None


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
