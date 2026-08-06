"""Module 13 - Export full medical report (PDF / Word)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_patient, get_current_user
from app.core.database import get_db
from app.models.patient import Patient
from app.models.user import User
from app.services import report

router = APIRouter(prefix="/export", tags=["export"])

_DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


@router.get("/report.pdf")
def export_pdf(
    user: User = Depends(get_current_user),
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> Response:
    data = report.gather_report_data(db, patient, user)
    pdf = report.render_pdf(data)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=raport-medical.pdf"},
    )


@router.get("/report.docx")
def export_docx(
    user: User = Depends(get_current_user),
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> Response:
    data = report.gather_report_data(db, patient, user)
    docx = report.render_docx(data)
    return Response(
        content=docx,
        media_type=_DOCX_MIME,
        headers={"Content-Disposition": "attachment; filename=raport-medical.docx"},
    )
