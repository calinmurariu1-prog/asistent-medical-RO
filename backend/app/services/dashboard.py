"""Module 12 - aggregated dashboard overview."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.document import Document
from app.models.enums import AppointmentStatus, NotificationStatus
from app.models.medication import Medication
from app.models.notification import Notification
from app.models.patient import Patient
from app.models.user import User
from app.services import lab_analysis, recommendations


def build_overview(db: Session, patient: Patient, user: User) -> dict:
    lab_summary = lab_analysis.build_summary(db, patient.id)

    recent_documents = db.scalars(
        select(Document)
        .where(Document.patient_id == patient.id)
        .order_by(Document.created_at.desc())
        .limit(5)
    ).all()

    active_medications = db.scalars(
        select(Medication).where(
            Medication.patient_id == patient.id, Medication.is_active.is_(True)
        )
    ).all()

    upcoming = db.scalars(
        select(Appointment)
        .where(
            Appointment.patient_id == patient.id,
            Appointment.starts_at >= datetime.now(UTC),
            Appointment.status == AppointmentStatus.SCHEDULED,
        )
        .order_by(Appointment.starts_at)
        .limit(5)
    ).all()

    unread = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.user_id == user.id,
            Notification.status != NotificationStatus.READ,
            or_(Notification.scheduled_for.is_(None),
                Notification.scheduled_for <= datetime.now(UTC)),
        )
    )

    rec = recommendations.build_recommendations(db, patient)

    return {
        "lab_summary": {
            "total_analytes": lab_summary["total_analytes"],
            "abnormal_count": lab_summary["abnormal_count"],
            "critical_count": lab_summary["critical_count"],
            "unknown_count": lab_summary["unknown_count"],
        },
        "recent_documents": [
            {
                "id": d.id,
                "original_filename": d.original_filename,
                "category": d.category.value,
                "status": d.status.value,
                "created_at": d.created_at,
            }
            for d in recent_documents
        ],
        "active_medications": [
            {"id": m.id, "name": m.name, "dose": m.dose} for m in active_medications
        ],
        "upcoming_appointments": [
            {"id": a.id, "title": a.title, "starts_at": a.starts_at} for a in upcoming
        ],
        "alerts": rec.alerts,
        "recommendations_preview": rec.questions_for_doctor[:5],
        "unread_notifications": int(unread or 0),
    }
