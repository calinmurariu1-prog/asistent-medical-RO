"""Module 7 - Orientative AI recommendations."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_patient
from app.core.database import get_db
from app.models.patient import Patient
from app.schemas.recommendation import RecommendationsOut
from app.services import recommendations

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=RecommendationsOut)
def get_recommendations(
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> RecommendationsOut:
    rec = recommendations.build_recommendations(db, patient)
    return RecommendationsOut(**rec.__dict__)
