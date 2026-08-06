"""Gather relevant context from the patient's record for the AI chat.

This is a keyword/lexical retriever over the patient's documents and structured
records. It is deterministic and works fully offline, so the chat is grounded
even without an embedding backend. The production upgrade is a vector retriever
(pgvector + embeddings) exposing the same `build_context` signature — the chat
service does not need to change.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.clinical import MedicalHistory
from app.models.document import Document, LabResult
from app.models.medication import Medication
from app.models.patient import Allergy

_STOPWORDS = {
    "si", "sa", "la", "de", "ce", "in", "un", "o", "cu", "pe", "am", "ai",
    "este", "sunt", "mea", "meu", "care", "ca", "pentru", "din", "mai",
    "the", "a", "an", "is", "are", "my", "what", "how", "to", "of",
}


@dataclass
class Snippet:
    text: str
    source: dict
    score: float = 0.0


@dataclass
class RetrievedContext:
    context_text: str
    sources: list[dict] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.sources


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[a-zăâîșț0-9]+", text.lower())
    return {t for t in tokens if len(t) > 2 and t not in _STOPWORDS}


def _collect_snippets(db: Session, patient_id: int) -> list[Snippet]:
    snippets: list[Snippet] = []

    documents = db.scalars(
        select(Document).where(Document.patient_id == patient_id)
    ).all()
    for doc in documents:
        body = doc.ai_summary or doc.extracted_text
        if body:
            snippets.append(
                Snippet(
                    text=f"[{doc.category.value}] {doc.original_filename}: {body[:1500]}",
                    source={
                        "type": "document",
                        "id": doc.id,
                        "title": doc.original_filename,
                        "category": doc.category.value,
                    },
                )
            )

    labs = db.scalars(
        select(LabResult).where(LabResult.patient_id == patient_id)
    ).all()
    for lab in labs:
        ref = (
            f" (referință {lab.ref_low}-{lab.ref_high})"
            if lab.ref_low is not None and lab.ref_high is not None
            else ""
        )
        when = f" la {lab.measured_on}" if lab.measured_on else ""
        snippets.append(
            Snippet(
                text=(
                    f"Analiză {lab.analyte}: {lab.value} {lab.unit or ''}{ref} "
                    f"[{lab.flag.value}]{when}."
                ),
                source={"type": "lab_result", "id": lab.id, "title": lab.analyte},
            )
        )

    history = db.scalars(
        select(MedicalHistory).where(MedicalHistory.patient_id == patient_id)
    ).all()
    for h in history:
        when = f" ({h.event_date})" if h.event_date else ""
        snippets.append(
            Snippet(
                text=f"Istoric [{h.event_type.value}] {h.title}{when}. {h.description or ''}",
                source={"type": "medical_history", "id": h.id, "title": h.title},
            )
        )

    meds = db.scalars(
        select(Medication).where(
            Medication.patient_id == patient_id, Medication.is_active.is_(True)
        )
    ).all()
    for m in meds:
        snippets.append(
            Snippet(
                text=f"Medicament activ: {m.name} {m.dose or ''} {m.frequency or ''}".strip(),
                source={"type": "medication", "id": m.id, "title": m.name},
            )
        )

    allergies = db.scalars(
        select(Allergy).where(Allergy.patient_id == patient_id)
    ).all()
    for a in allergies:
        snippets.append(
            Snippet(
                text=f"Alergie: {a.substance} (severitate {a.severity.value}).",
                source={"type": "allergy", "id": a.id, "title": a.substance},
            )
        )

    return snippets


def build_context(
    db: Session, patient_id: int, query: str, *, max_snippets: int = 8
) -> RetrievedContext:
    """Return the most relevant record snippets for a query, with source refs."""
    snippets = _collect_snippets(db, patient_id)
    if not snippets:
        return RetrievedContext(context_text="", sources=[])

    query_tokens = _tokenize(query)
    for s in snippets:
        overlap = len(query_tokens & _tokenize(s.text))
        # Small baseline so that, with an unrelated query, we still surface the
        # record (better to ground on something than to answer from nothing).
        s.score = overlap + 0.01

    ranked = sorted(snippets, key=lambda s: s.score, reverse=True)[:max_snippets]

    lines: list[str] = []
    sources: list[dict] = []
    for i, snip in enumerate(ranked, start=1):
        lines.append(f"[S{i}] {snip.text}")
        sources.append({"ref": f"S{i}", **snip.source})

    return RetrievedContext(context_text="\n".join(lines), sources=sources)
