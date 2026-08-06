"""Module 8 - Chronic disease monitoring dashboard & charts."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_patient
from app.core.database import get_db
from app.models.patient import Patient
from app.schemas.monitoring import MonitoringDashboardOut, MonitoringParam
from app.services import monitoring

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/dashboard", response_model=MonitoringDashboardOut)
def dashboard(
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> MonitoringDashboardOut:
    result = monitoring.build_dashboard(db, patient)
    groups = {
        group: [MonitoringParam(**p.__dict__) for p in params]
        for group, params in result.groups.items()
    }
    return MonitoringDashboardOut(
        chronic_conditions=result.chronic_conditions,
        groups=groups,
        bmi=result.bmi,
    )


@router.get("/parameters", response_model=dict[str, str])
def supported_parameters() -> dict[str, str]:
    """Map of supported monitoring analytes to their clinical group."""
    return {label: group for label, group in monitoring.MONITORING_ANALYTES.values()}
