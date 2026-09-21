"""Data-aware AI features that read the patient's record (summary, comparison).

Unlike free-text skills, these gather the patient's own data first, then run the
AI provider. The offline mock produces a deterministic result from the data.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.medication import Medication
from app.models.patient import Patient
from app.services import lab_analysis, monitoring
from app.services.ai.base import DISCLAIMER, AIProvider

_GUARD = (
    "Ești un asistent medical informativ, în română. NU pui diagnostic și NU "
    "prescrii tratament. Rezumă clar și empatic, orientativ."
)


def _with_disclaimer(text: str) -> str:
    return text if "orientativ" in text.lower() else f"{text}\n\n{DISCLAIMER}"


def _gather_record(db: Session, patient: Patient) -> dict:
    summary = lab_analysis.build_summary(db, patient.id)
    abnormal = [i for i in summary["items"] if i["flag"] in lab_analysis.ABNORMAL_FLAGS]
    meds = db.scalars(
        select(Medication).where(
            Medication.patient_id == patient.id, Medication.is_active.is_(True)
        )
    ).all()
    conditions = monitoring.build_dashboard(db, patient).chronic_conditions
    return {
        "total_analytes": summary["total_analytes"],
        "unknown_count": summary["unknown_count"],
        "abnormal": abnormal,
        "medications": [m.name for m in meds],
        "conditions": conditions,
    }


def summarize_record(db: Session, ai: AIProvider, patient: Patient) -> str:
    rec = _gather_record(db, patient)

    lines = [
        f"Analize urmărite: {rec['total_analytes']}, dintre care "
        f"{len(rec['abnormal'])} în afara intervalului.",
    ]
    if rec["unknown_count"]:
        lines.append(f"Rezultate neevaluabile din datele disponibile: {rec['unknown_count']}.")
    if rec["abnormal"]:
        vals = ", ".join(
            f"{i['analyte']} ({i['flag']})" for i in rec["abnormal"][:6]
        )
        lines.append(f"Valori de discutat cu medicul: {vals}.")
    if rec["conditions"]:
        lines.append(f"Afecțiuni cronice: {', '.join(rec['conditions'])}.")
    if rec["medications"]:
        lines.append(f"Tratamente active: {', '.join(rec['medications'])}.")
    context = "\n".join(lines)

    if getattr(ai, "name", "") == "mock":
        return _with_disclaimer("Rezumatul dosarului tău:\n" + context)

    user = (
        "Rezumă starea de sănătate a pacientului pe baza datelor de mai jos, în "
        "3-5 propoziții, cu ton empatic și orientativ:\n\n" + context
    )
    return _with_disclaimer(ai.complete(system=_GUARD, user=user))


def compare_analyte(db: Session, ai: AIProvider, patient: Patient, analyte: str) -> str:
    series = lab_analysis.build_series(db, patient.id, analyte)
    numeric = [r for r in series if r.value is not None]
    if not numeric:
        return f"Nu există valori numerice pentru {analyte}."
    if len(numeric) < 2:
        return (
            f"Există o singură măsurătoare pentru {analyte} "
            f"({numeric[0].value} {numeric[0].unit or ''}). "
            "Sunt necesare cel puțin două pentru comparație."
        )

    warning = lab_analysis.comparison_warning(series)
    if warning:
        return warning
    trend = lab_analysis.compute_trend(series)
    first, last = numeric[0], numeric[-1]
    facts = (
        f"{analyte}: {len(numeric)} măsurători, de la {first.value} "
        f"{first.unit or ''} ({first.measured_on}) la {last.value} "
        f"{last.unit or ''} ({last.measured_on}). Tendință: {trend}."
    )

    if getattr(ai, "name", "") == "mock":
        return _with_disclaimer(f"Evoluția analizei {analyte}:\n{facts}")

    user = (
        "Interpretează orientativ evoluția acestei analize pentru pacient, în "
        "2-4 propoziții:\n\n" + facts
    )
    return _with_disclaimer(ai.complete(system=_GUARD, user=user))
