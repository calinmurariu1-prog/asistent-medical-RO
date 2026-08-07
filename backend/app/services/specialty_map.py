"""Map detected health problems to the medical specialty to look for (Module: providers).

Derives specialty suggestions from the patient's abnormal lab values and chronic
conditions — the same signals used by monitoring/recommendations.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.services import lab_analysis, monitoring

# Normalized analyte -> specialty.
_SPECIALTY_BY_ANALYTE: dict[str, str] = {
    "glicemie": "Diabetolog",
    "hba1c": "Diabetolog",
    "tsh": "Endocrinolog",
    "colesterol total": "Cardiolog",
    "ldl": "Cardiolog",
    "hdl": "Cardiolog",
    "trigliceride": "Cardiolog",
    "tensiune sistolica": "Cardiolog",
    "tensiune diastolica": "Cardiolog",
    "puls": "Cardiolog",
    "creatinina": "Nefrolog",
    "tgp": "Gastroenterolog",
    "tgo": "Gastroenterolog",
    "hemoglobina": "Hematolog",
}

# Substring in a chronic-condition title -> specialty.
_SPECIALTY_BY_CONDITION: dict[str, str] = {
    "diabet": "Diabetolog",
    "tiroid": "Endocrinolog",
    "hipertensiune": "Cardiolog",
    "cardio": "Cardiolog",
    "renal": "Nefrolog",
    "rinichi": "Nefrolog",
    "hepat": "Gastroenterolog",
    "ficat": "Gastroenterolog",
    "astm": "Pneumolog",
    "bpoc": "Pneumolog",
    "endometrioz": "Ginecolog",
}

_ABNORMAL = {"high", "low", "critical_high", "critical_low"}
_FLAG_LABEL = {
    "high": "crescută",
    "low": "scăzută",
    "critical_high": "critic crescută",
    "critical_low": "critic scăzută",
}


@dataclass
class SpecialtySuggestion:
    specialty: str
    reasons: list[str] = field(default_factory=list)


def _normalize(text: str) -> str:
    table = str.maketrans("ăâîșțĂÂÎȘȚ", "aaistAAIST")
    return text.strip().lower().translate(table)


def specialties_for_patient(db: Session, patient: Patient) -> list[SpecialtySuggestion]:
    """Ordered, de-duplicated specialties relevant to this patient's data."""
    by_specialty: dict[str, list[str]] = {}

    def add(specialty: str, reason: str) -> None:
        by_specialty.setdefault(specialty, [])
        if reason not in by_specialty[specialty]:
            by_specialty[specialty].append(reason)

    # Abnormal lab values.
    summary = lab_analysis.build_summary(db, patient.id)
    for item in summary["items"]:
        flag = item["flag"]
        if flag not in _ABNORMAL:
            continue
        specialty = _SPECIALTY_BY_ANALYTE.get(_normalize(item["analyte"]))
        if specialty:
            label = _FLAG_LABEL.get(flag, str(flag))
            add(specialty, f"Analiza {item['analyte']} este {label}.")

    # Chronic conditions.
    for cond in monitoring.build_dashboard(db, patient).chronic_conditions:
        norm = _normalize(cond)
        for key, specialty in _SPECIALTY_BY_CONDITION.items():
            if key in norm:
                add(specialty, f"Afecțiune cronică: {cond}.")
                break

    suggestions = [
        SpecialtySuggestion(specialty=s, reasons=r) for s, r in by_specialty.items()
    ]
    # Always offer the family doctor as a safe default.
    if not suggestions:
        suggestions.append(
            SpecialtySuggestion(
                specialty="Medic de familie",
                reasons=["Nicio problemă specifică detectată în date."],
            )
        )
    return suggestions
