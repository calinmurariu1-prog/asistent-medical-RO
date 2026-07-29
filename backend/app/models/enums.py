"""Enumerations shared across models."""
from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"


class Sex(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNSPECIFIED = "unspecified"


class BloodType(str, enum.Enum):
    A_POS = "A+"
    A_NEG = "A-"
    B_POS = "B+"
    B_NEG = "B-"
    AB_POS = "AB+"
    AB_NEG = "AB-"
    O_POS = "O+"
    O_NEG = "O-"
    UNKNOWN = "unknown"


class DocumentCategory(str, enum.Enum):
    LAB = "lab"                     # analize laborator
    CT = "ct"
    MRI = "mri"                     # RMN
    ULTRASOUND = "ultrasound"       # ecografie
    XRAY = "xray"                   # radiografie
    MEDICAL_LETTER = "medical_letter"   # scrisoare medicala
    DISCHARGE = "discharge"         # bilet externare
    PRESCRIPTION = "prescription"   # reteta
    RECOMMENDATION = "recommendation"
    OTHER = "other"


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class LabFlag(str, enum.Enum):
    NORMAL = "normal"
    HIGH = "high"
    LOW = "low"
    CRITICAL_HIGH = "critical_high"
    CRITICAL_LOW = "critical_low"


class MedicalEventType(str, enum.Enum):
    DIAGNOSIS = "diagnosis"
    PROCEDURE = "procedure"
    SURGERY = "surgery"
    HOSPITALIZATION = "hospitalization"
    VACCINE = "vaccine"
    TREATMENT = "treatment"
    CHRONIC_CONDITION = "chronic_condition"
    FAMILY_HISTORY = "family_history"


class AppointmentType(str, enum.Enum):
    CONSULTATION = "consultation"
    INVESTIGATION = "investigation"
    LAB = "lab"
    OTHER = "other"


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    MISSED = "missed"


class NotificationChannel(str, enum.Enum):
    PUSH = "push"
    EMAIL = "email"
    SMS = "sms"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    READ = "read"


class ChatRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class AllergySeverity(str, enum.Enum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    UNKNOWN = "unknown"


class ConsentType(str, enum.Enum):
    DATA_PROCESSING = "data_processing"
    AI_PROCESSING = "ai_processing"
    MARKETING = "marketing"
    DATA_SHARING = "data_sharing"
