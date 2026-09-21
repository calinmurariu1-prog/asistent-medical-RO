"""Module 5 - lab interpretation: time series, summaries and AI explanations."""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.document import LabResult
from app.models.enums import LabFlag
from app.services.ai.base import DISCLAIMER, AIProvider
from app.services.ai.lab_units import normalize_unit

ABNORMAL_FLAGS = {
    LabFlag.HIGH,
    LabFlag.LOW,
    LabFlag.CRITICAL_HIGH,
    LabFlag.CRITICAL_LOW,
}
CRITICAL_FLAGS = {LabFlag.CRITICAL_HIGH, LabFlag.CRITICAL_LOW}


def _sort_key(r: LabResult) -> tuple:
    # Undated results sort first (date.min); ties broken by insertion id.
    return (r.measured_on or date.min, r.id)


def get_results(
    db: Session,
    patient_id: int,
    *,
    analyte: str | None = None,
    flag: LabFlag | None = None,
) -> list[LabResult]:
    stmt = select(LabResult).where(LabResult.patient_id == patient_id)
    if analyte:
        stmt = stmt.where(LabResult.analyte == analyte)
    if flag:
        stmt = stmt.where(LabResult.flag == flag)
    results = list(db.scalars(stmt).all())
    results.sort(key=_sort_key)
    return results


def build_series(db: Session, patient_id: int, analyte: str) -> list[LabResult]:
    """Chronological values for a single analyte (for charts / comparison)."""
    return get_results(db, patient_id, analyte=analyte)


def comparison_warning(series: list[LabResult]) -> str | None:
    """Require explicit compatible units and distinct dates before comparison."""
    if any(r.confidence == "unverified" for r in series):
        return "Comparație indisponibilă: există valori de confirmat pe documentul original."
    numeric = [r for r in series if r.value is not None]
    if any(not r.unit or not r.unit.strip() for r in numeric):
        return "Comparație indisponibilă: lipsesc unități de măsură. Verifică originalele."
    if len({normalize_unit(r.unit) for r in numeric}) > 1:
        return "Comparație indisponibilă: unitățile diferă. Este necesară o conversie validată."
    dates = [r.measured_on for r in numeric]
    if any(d is None for d in dates) or len(set(dates)) != len(dates):
        return ("Comparație indisponibilă: date lipsă sau măsurători în aceeași zi. "
                "Verifică ordinea.")
    return None


def compute_trend(series: list[LabResult]) -> str | None:
    """Describe the last value relative to the previous one."""
    numeric = [r for r in series if r.value is not None]
    if comparison_warning(series) or len(numeric) < 2:
        return None
    prev, last = numeric[-2].value, numeric[-1].value
    if last > prev:
        return f"în creștere ({prev} → {last})"
    if last < prev:
        return f"în scădere ({prev} → {last})"
    return f"stabilă ({last})"


def build_summary(db: Session, patient_id: int) -> dict:
    """Latest value per analyte + counts of abnormal/critical results."""
    results = get_results(db, patient_id)
    by_analyte: dict[str, list[LabResult]] = defaultdict(list)
    for r in results:
        by_analyte[r.analyte].append(r)

    items = []
    abnormal = critical = unknown = 0
    for analyte, series in sorted(by_analyte.items()):
        series.sort(key=_sort_key)
        latest = series[-1]
        effective_flag = LabFlag.UNKNOWN if latest.confidence == "unverified" else latest.flag
        if effective_flag == LabFlag.UNKNOWN:
            unknown += 1
        if effective_flag in ABNORMAL_FLAGS:
            abnormal += 1
        if effective_flag in CRITICAL_FLAGS:
            critical += 1
        items.append(
            {
                "analyte": analyte,
                "latest_value": latest.value if latest.confidence == "verified" else None,
                "unit": latest.unit,
                "flag": effective_flag,
                "measured_on": latest.measured_on,
                "measurements": len(series),
                "trend": compute_trend(series),
            }
        )
    return {
        "total_analytes": len(items),
        "abnormal_count": abnormal,
        "critical_count": critical,
        "unknown_count": unknown,
        "items": items,
    }


def explain_result(db: Session, ai: AIProvider, result: LabResult) -> LabResult:
    """Generate and persist an AI explanation for one lab result."""
    if result.confidence != "verified":
        result.ai_explanation = (
            "Această valoare nu este confirmată din documentul original. "
            f"Verifică valoarea, unitatea și intervalul înainte de interpretare. {DISCLAIMER}"
        )
        db.commit()
        db.refresh(result)
        return result
    series = build_series(db, result.patient_id, result.analyte)
    trend = compute_trend(series)
    result.ai_explanation = ai.explain_lab_value(
        analyte=result.analyte,
        value=result.value,
        unit=result.unit,
        ref_low=result.ref_low,
        ref_high=result.ref_high,
        flag=result.flag.value,
        trend=trend,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def invalidate_explanations(db: Session, patient_id: int, analytes: list[str]) -> None:
    """Cached comparisons are stale when any value/date in the series changes."""
    if analytes:
        db.execute(update(LabResult).where(
            LabResult.patient_id == patient_id, LabResult.analyte.in_(set(analytes)),
        ).values(ai_explanation=None))
