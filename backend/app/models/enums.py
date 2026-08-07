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


class HealthSource(str, enum.Enum):
    """Origin of an imported health metric."""

    APPLE_HEALTH = "apple_health"
    GOOGLE_HEALTH = "google_health"       # Google Fit / Health Connect / Takeout
    HUAWEI_HEALTH = "huawei_health"
    MANUAL = "manual"


class HealthMetricType(str, enum.Enum):
    """Canonical (normalized) health metric types.

    Every provider's own identifiers are mapped onto these, together with a
    canonical unit, so the rest of the app never sees vendor-specific codes.
    """

    STEPS = "steps"                                   # count
    HEART_RATE = "heart_rate"                         # bpm
    RESTING_HEART_RATE = "resting_heart_rate"         # bpm
    BLOOD_PRESSURE_SYSTOLIC = "blood_pressure_systolic"   # mmHg
    BLOOD_PRESSURE_DIASTOLIC = "blood_pressure_diastolic" # mmHg
    BLOOD_GLUCOSE = "blood_glucose"                   # mg/dL
    OXYGEN_SATURATION = "oxygen_saturation"           # %
    BODY_WEIGHT = "body_weight"                       # kg
    HEIGHT = "height"                                 # cm
    BODY_FAT = "body_fat"                             # %
    BODY_TEMPERATURE = "body_temperature"             # °C
    RESPIRATORY_RATE = "respiratory_rate"             # rpm
    SLEEP = "sleep"                                   # min
    ACTIVE_ENERGY = "active_energy"                   # kcal
    DISTANCE = "distance"                             # km
    VO2MAX = "vo2max"                                 # mL/kg/min


# Canonical unit for each metric type (what we store).
HEALTH_METRIC_UNITS: dict[HealthMetricType, str] = {
    HealthMetricType.STEPS: "count",
    HealthMetricType.HEART_RATE: "bpm",
    HealthMetricType.RESTING_HEART_RATE: "bpm",
    HealthMetricType.BLOOD_PRESSURE_SYSTOLIC: "mmHg",
    HealthMetricType.BLOOD_PRESSURE_DIASTOLIC: "mmHg",
    HealthMetricType.BLOOD_GLUCOSE: "mg/dL",
    HealthMetricType.OXYGEN_SATURATION: "%",
    HealthMetricType.BODY_WEIGHT: "kg",
    HealthMetricType.HEIGHT: "cm",
    HealthMetricType.BODY_FAT: "%",
    HealthMetricType.BODY_TEMPERATURE: "°C",
    HealthMetricType.RESPIRATORY_RATE: "rpm",
    HealthMetricType.SLEEP: "min",
    HealthMetricType.ACTIVE_ENERGY: "kcal",
    HealthMetricType.DISTANCE: "km",
    HealthMetricType.VO2MAX: "mL/kg/min",
}

# Romanian labels for UI.
HEALTH_METRIC_LABELS: dict[HealthMetricType, str] = {
    HealthMetricType.STEPS: "Pași",
    HealthMetricType.HEART_RATE: "Puls",
    HealthMetricType.RESTING_HEART_RATE: "Puls în repaus",
    HealthMetricType.BLOOD_PRESSURE_SYSTOLIC: "Tensiune sistolică",
    HealthMetricType.BLOOD_PRESSURE_DIASTOLIC: "Tensiune diastolică",
    HealthMetricType.BLOOD_GLUCOSE: "Glicemie",
    HealthMetricType.OXYGEN_SATURATION: "Saturație oxigen (SpO₂)",
    HealthMetricType.BODY_WEIGHT: "Greutate",
    HealthMetricType.HEIGHT: "Înălțime",
    HealthMetricType.BODY_FAT: "Grăsime corporală",
    HealthMetricType.BODY_TEMPERATURE: "Temperatură",
    HealthMetricType.RESPIRATORY_RATE: "Frecvență respiratorie",
    HealthMetricType.SLEEP: "Somn",
    HealthMetricType.ACTIVE_ENERGY: "Energie activă",
    HealthMetricType.DISTANCE: "Distanță",
    HealthMetricType.VO2MAX: "VO₂ max",
}
