"""Module 8 - chronic-condition monitoring dashboard.

Reuses the time-series stored in `lab_results` (fed by document extraction or
manual entry) and groups recognized parameters by clinical area. No new table:
vitals like weight/pulse/blood pressure are recorded as lab analytes too.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.clinical import MedicalHistory
from app.models.document import LabResult
from app.models.enums import MedicalEventType
from app.models.patient import Patient
from app.services import lab_analysis

# Normalized analyte -> (display label, clinical group).
MONITORING_ANALYTES: dict[str, tuple[str, str]] = {
    "glicemie": ("Glicemie", "Diabet"),
    "hba1c": ("HbA1c", "Diabet"),
    "colesterol total": ("Colesterol total", "Cardiovascular"),
    "ldl": ("LDL colesterol", "Cardiovascular"),
    "hdl": ("HDL colesterol", "Cardiovascular"),
    "trigliceride": ("Trigliceride", "Cardiovascular"),
    "tensiune sistolica": ("Tensiune sistolică", "Cardiovascular"),
    "tensiune diastolica": ("Tensiune diastolică", "Cardiovascular"),
    "puls": ("Puls", "Cardiovascular"),
    "tsh": ("TSH", "Tiroidă"),
    "creatinina": ("Creatinină", "Renal"),
    "tgp": ("TGP (ALT)", "Hepatic"),
    "tgo": ("TGO (AST)", "Hepatic"),
    "greutate": ("Greutate", "General"),
}

_ALIASES = {
    "colesterol": "colesterol total",
    "alt": "tgp",
    "ast": "tgo",
    "ldl colesterol": "ldl",
    "hdl colesterol": "hdl",
}


@dataclass
class ParamSummary:
    analyte: str
    label: str
    group: str
    unit: str | None
    latest_value: float | None
    flag: str
    trend: str | None
    points: list[dict]


@dataclass
class MonitoringDashboard:
    chronic_conditions: list[str] = field(default_factory=list)
    groups: dict[str, list[ParamSummary]] = field(default_factory=dict)
    bmi: float | None = None


def _normalize(analyte: str) -> str:
    table = str.maketrans("ăâîșțĂÂÎȘȚ", "aaistAAIST")
    key = analyte.strip().lower().translate(table)
    return _ALIASES.get(key, key)


def _chronic_conditions(db: Session, patient_id: int) -> list[str]:
    stmt = select(MedicalHistory).where(
        MedicalHistory.patient_id == patient_id,
        (MedicalHistory.is_chronic.is_(True))
        | (MedicalHistory.event_type == MedicalEventType.CHRONIC_CONDITION),
    )
    return [h.title for h in db.scalars(stmt).all()]


def build_dashboard(db: Session, patient: Patient) -> MonitoringDashboard:
    dashboard = MonitoringDashboard(
        chronic_conditions=_chronic_conditions(db, patient.id)
    )

    distinct = db.scalars(
        select(LabResult.analyte)
        .where(LabResult.patient_id == patient.id)
        .distinct()
    ).all()

    for stored in distinct:
        meta = MONITORING_ANALYTES.get(_normalize(stored))
        if meta is None:
            continue
        label, group = meta
        series = lab_analysis.build_series(db, patient.id, stored)
        if not series:
            continue
        latest = series[-1]
        dashboard.groups.setdefault(group, []).append(
            ParamSummary(
                analyte=stored,
                label=label,
                group=group,
                unit=latest.unit,
                latest_value=latest.value,
                flag=latest.flag.value,
                trend=lab_analysis.compute_trend(series),
                points=[
                    {
                        "measured_on": r.measured_on.isoformat()
                        if r.measured_on
                        else None,
                        "value": r.value,
                        "flag": r.flag.value,
                    }
                    for r in series
                ],
            )
        )

    if patient.weight_kg and patient.height_cm:
        h = patient.height_cm / 100
        dashboard.bmi = round(patient.weight_kg / (h * h), 1)

    return dashboard
