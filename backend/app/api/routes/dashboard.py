"""Module 12 - Aggregated dashboard."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_patient, get_current_user
from app.core.database import get_db
from app.models.patient import Patient
from app.models.user import User
from app.schemas.dashboard import DashboardOut
from app.services import dashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
def get_dashboard(
    user: User = Depends(get_current_user),
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> DashboardOut:
    return DashboardOut(**dashboard.build_overview(db, patient, user))
