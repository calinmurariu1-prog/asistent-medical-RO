"""GDPR data access & erasure (Art. 15/17/20)."""
from __future__ import annotations

import json
from datetime import UTC, date, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chat import AIChat
from app.models.document import Document
from app.models.feedback import Feedback
from app.models.medication import Medication
from app.models.medication_reminder import MedicationReminder
from app.models.patient import Patient
from app.models.user import Consent, User
from app.services.storage_cleanup import enqueue


def _iso(value: date | datetime | None) -> str | None:
    if isinstance(value, datetime):
        return value.replace(tzinfo=value.tzinfo or UTC).isoformat()
    return value.isoformat() if value else None


def _record(row) -> dict:
    return {"id": row.id, "created_at": _iso(row.created_at), "updated_at": _iso(row.updated_at)}


def _json(value: str | None, default):
    if value is None:
        return default
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        # Preserve malformed legacy content instead of preventing the entire export.
        return {"unparsed_text": value}


def export_user_data(db: Session, user: User) -> dict:
    """Export the supported account and clinical sections with explicit scope limits."""
    patient = db.scalar(select(Patient).where(Patient.user_id == user.id))

    data: dict = {
        "export_metadata": {
            "schema_version": 2,
            "exported_at": _iso(datetime.now(UTC)),
            "original_files_included": False,
            "scope": "account_and_clinical_records",
            "not_included": ["original_file_bytes", "cnp", "health_device_data",
                             "notifications", "feedback", "billing", "audit_logs",
                             "authentication_secrets"],
        },
        "account": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "is_email_verified": user.is_email_verified,
            "mfa_enabled": user.mfa_enabled,
            "created_at": user.created_at.isoformat(),
        },
        "consents": [
            {
                "type": c.consent_type.value,
                "granted": c.granted,
                "version": c.version,
                "created_at": c.created_at.isoformat(),
            }
            for c in db.scalars(select(Consent).where(Consent.user_id == user.id))
        ],
    }

    if patient is None:
        data["patient"] = None
        return data

    data["patient"] = {
        **_record(patient),
        "family_doctor_id": patient.family_doctor_id,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "birth_date": patient.birth_date.isoformat() if patient.birth_date else None,
        "sex": patient.sex.value if patient.sex else None,
        "weight_kg": patient.weight_kg,
        "height_cm": patient.height_cm,
        "blood_type": patient.blood_type.value if patient.blood_type else None,
        "phone": patient.phone,
        # CNP is intentionally NOT decrypted into the export by default.
    }
    data["emergency_contacts"] = [
        {**_record(c), "name": c.name, "relationship_label": c.relationship_label, "phone": c.phone}
        for c in patient.emergency_contacts
    ]
    data["allergies"] = [
        {**_record(a), "substance": a.substance, "reaction": a.reaction,
         "severity": a.severity.value}
        for a in patient.allergies
    ]
    data["vaccines"] = [
        {**_record(v), "name": v.name, "dose": v.dose, "provider": v.provider,
         "administered_on": v.administered_on.isoformat() if v.administered_on else None}
        for v in patient.vaccines
    ]
    data["medical_history"] = [
        {**_record(h), "diagnosis_id": h.diagnosis_id, "procedure_id": h.procedure_id,
         "doctor_id": h.doctor_id, "hospital_id": h.hospital_id,
         "event_type": h.event_type.value, "title": h.title, "description": h.description,
         "event_date": h.event_date.isoformat() if h.event_date else None,
         "is_chronic": h.is_chronic}
        for h in patient.medical_history
    ]
    data["lab_results"] = [
        {**_record(lr), "document_id": lr.document_id, "loinc_code": lr.loinc_code,
         "value_text": lr.value_text, "confidence": lr.confidence,
         "ai_explanation": lr.ai_explanation, "analyte": lr.analyte,
         "value": lr.value, "unit": lr.unit,
         "ref_low": lr.ref_low, "ref_high": lr.ref_high, "flag": lr.flag.value,
         "measured_on": lr.measured_on.isoformat() if lr.measured_on else None}
        for lr in patient.lab_results
    ]
    data["documents"] = [
        {**_record(d), "document_date": _iso(d.document_date),
         "content_type": d.content_type, "size_bytes": d.size_bytes,
         "extracted_text": d.extracted_text, "ai_metadata": _json(d.ai_metadata, None),
         "processed_at": _iso(d.processed_at),
         "original_download_path": f"/api/v1/documents/{d.id}/original",
         "filename": d.original_filename, "category": d.category.value,
         "status": d.status.value, "ai_summary": d.ai_summary,
         "created_at": d.created_at.isoformat()}
        for d in patient.documents
    ]
    data["medications"] = [
        {**_record(m), "interval": m.interval, "start_date": _iso(m.start_date),
         "end_date": _iso(m.end_date), "notes": m.notes, "name": m.name,
         "active_substance": m.active_substance, "dose": m.dose,
         "frequency": m.frequency, "is_active": m.is_active}
        for m in patient.medications
    ]
    data["medication_reminders"] = [
        {**_record(r), "medication_id": r.medication_id, "local_time": r.local_time,
         "timezone": r.timezone, "is_enabled": r.is_enabled,
         "next_occurrence": (r.next_occurrence.replace(tzinfo=r.next_occurrence.tzinfo or UTC)
                             .isoformat() if r.next_occurrence else None)}
        for r in db.scalars(select(MedicationReminder).join(Medication).where(
            Medication.patient_id == patient.id))
    ]
    data["appointments"] = [
        {**_record(a), "location": a.location, "doctor_id": a.doctor_id, "notes": a.notes,
         "ends_at": _iso(a.ends_at),
         "title": a.title, "type": a.type.value, "starts_at": _iso(a.starts_at),
         "status": a.status.value}
        for a in patient.appointments
    ]
    data["chats"] = [
        {
            **_record(chat),
            "title": chat.title,
            "created_at": chat.created_at.isoformat(),
            "messages": [
                {**_record(msg), "role": msg.role.value, "content": msg.content,
                 "sources": _json(msg.sources, [])}
                for msg in chat.messages
            ],
        }
        for chat in db.scalars(select(AIChat).where(AIChat.patient_id == patient.id))
    ]
    return data


def delete_user(db: Session, user: User) -> list[str]:
    """Erase the account and all owned data (cascades via FKs/relationships)."""
    keys = list(db.scalars(select(Document.storage_key).join(Patient).where(
        Patient.user_id == user.id)))
    jobs = enqueue(db, keys)
    if not settings.is_production:
        jobs += enqueue(db, [user.email], backend="mailbox")
    db.execute(delete(Feedback).where(Feedback.user_id == user.id))
    db.delete(user)
    db.commit()
    return jobs
