"""Module 7 - orientative AI recommendations.

Rule-based over the patient's own data (abnormal labs, chronic conditions,
medication interactions). Deterministic and offline; every output is framed as
informative and paired with a disclaimer. An LLM can later enrich these via the
AIProvider abstraction without changing the API.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.medication import Medication
from app.models.patient import Patient
from app.services import lab_analysis, medication_check, monitoring
from app.services.ai.base import DISCLAIMER

_CRITICAL = {"critical_high", "critical_low"}
_ABNORMAL = {"high", "low", "critical_high", "critical_low"}
_METABOLIC = {"glicemie", "colesterol total", "ldl", "trigliceride", "hba1c"}


@dataclass
class Recommendations:
    questions_for_doctor: list[str] = field(default_factory=list)
    investigations: list[str] = field(default_factory=list)
    lifestyle: list[str] = field(default_factory=list)
    monitoring: list[str] = field(default_factory=list)
    alerts: list[str] = field(default_factory=list)
    disclaimer: str = DISCLAIMER


def _normalize(analyte: str) -> str:
    table = str.maketrans("ăâîșțĂÂÎȘȚ", "aaistAAIST")
    return analyte.strip().lower().translate(table)


def build_recommendations(db: Session, patient: Patient) -> Recommendations:
    rec = Recommendations()

    summary = lab_analysis.build_summary(db, patient.id)
    metabolic_flag = False
    for item in summary["items"]:
        flag = item["flag"]
        analyte = item["analyte"]
        if flag in _CRITICAL:
            rec.alerts.append(
                f"Valoare critică la {analyte} ({item['latest_value']} "
                f"{item['unit'] or ''}). Contactează medicul cât mai curând."
            )
        if flag in _ABNORMAL:
            rec.questions_for_doctor.append(
                f"Întreabă medicul ce înseamnă valoarea {analyte} ({flag})."
            )
            rec.monitoring.append(f"Monitorizează periodic {analyte}.")
            if _normalize(analyte) in _METABOLIC:
                metabolic_flag = True

    if metabolic_flag:
        rec.lifestyle.append(
            "Discută cu medicul despre o dietă echilibrată, redu zahărul și "
            "grăsimile saturate."
        )
        rec.lifestyle.append("Activitate fizică regulată (ex. 30 min/zi).")

    # Chronic conditions -> targeted monitoring suggestions.
    conditions = monitoring.build_dashboard(db, patient).chronic_conditions
    for cond in conditions:
        rec.investigations.append(
            f"Întreabă medicul ce investigații periodice sunt recomandate "
            f"pentru: {cond}."
        )

    # Medication interactions / duplicates -> pharmacist/doctor questions.
    meds = list(
        db.scalars(select(Medication).where(Medication.patient_id == patient.id)).all()
    )
    med_check = medication_check.check_medications(meds)
    for w in med_check.interactions:
        rec.questions_for_doctor.append(
            f"Verifică cu medicul/farmacistul posibila interacțiune între "
            f"{w.drug_a} și {w.drug_b}."
        )
    for d in med_check.duplicates:
        rec.questions_for_doctor.append(
            f"Întreabă dacă e necesar să iei mai multe medicamente cu aceeași "
            f"substanță ({d.substance}): {', '.join(d.medications)}."
        )

    # De-duplicate while preserving order.
    _fields = (
        "questions_for_doctor",
        "investigations",
        "lifestyle",
        "monitoring",
        "alerts",
    )
    for fieldname in _fields:
        seen: set[str] = set()
        deduped = []
        for line in getattr(rec, fieldname):
            if line not in seen:
                seen.add(line)
                deduped.append(line)
        setattr(rec, fieldname, deduped)

    return rec
