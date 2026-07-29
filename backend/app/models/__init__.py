"""SQLAlchemy models. Importing this package registers every table on Base.metadata."""
from app.models.appointment import Appointment
from app.models.chat import AIChat, AIChatMessage
from app.models.clinical import (
    Diagnosis,
    Doctor,
    Hospital,
    MedicalHistory,
    Procedure,
)
from app.models.document import Document, LabResult
from app.models.medication import Medication
from app.models.notification import Notification
from app.models.patient import (
    Allergy,
    EmergencyContact,
    Patient,
    Vaccine,
)
from app.models.user import AuditLog, Consent, User

__all__ = [
    "User",
    "Consent",
    "AuditLog",
    "Patient",
    "Allergy",
    "Vaccine",
    "EmergencyContact",
    "Doctor",
    "Hospital",
    "Diagnosis",
    "Procedure",
    "MedicalHistory",
    "Document",
    "LabResult",
    "Medication",
    "Appointment",
    "AIChat",
    "AIChatMessage",
    "Notification",
]
