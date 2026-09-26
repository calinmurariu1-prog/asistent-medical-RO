"""Transactional daily reminder cursor; local time, DST and treatment period aware."""
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.models.enums import NotificationChannel, NotificationStatus
from app.models.medication import Medication
from app.models.medication_reminder import MedicationReminder
from app.models.notification import Notification
from app.models.patient import Patient


def next_due(med: Medication, reminder: MedicationReminder, after: datetime) -> datetime | None:
    if not med.is_active or not reminder.is_enabled:
        return None
    zone = ZoneInfo(reminder.timezone)
    day = max(after.astimezone(zone).date(), med.start_date or after.astimezone(zone).date())
    clock = time.fromisoformat(reminder.local_time)
    for _ in range(370):
        if med.end_date and day > med.end_date:
            return None
        local = datetime.combine(day, clock).replace(tzinfo=zone, fold=0)
        candidate = local.astimezone(UTC)
        # Spring gap: skip this date; autumn fold: first occurrence only.
        if (candidate.astimezone(zone).replace(tzinfo=None) == local.replace(tzinfo=None)
                and candidate > after):
            return candidate
        day += timedelta(days=1)
    return None


def clear_notifications(db: Session, reminder_id: int) -> None:
    db.execute(delete(Notification).where(Notification.resource_type == "medication_reminder",
                                         Notification.resource_id == str(reminder_id)))


def enqueue(db: Session, med: Medication, reminder: MedicationReminder, user_id: int) -> None:
    if reminder.next_occurrence is None:
        return
    db.add(Notification(
        user_id=user_id, channel=NotificationChannel.PUSH, status=NotificationStatus.PENDING,
        title=f"Memento ales: {med.name}"[:300],
        body=f"Ora aleasă de tine: {reminder.local_time} ({reminder.timezone}). "
             "Consultă tratamentul înregistrat. Acest memento nu confirmă administrarea "
             "și nu recomandă recuperarea unei doze omise.",
        scheduled_for=reminder.next_occurrence, resource_type="medication_reminder",
        resource_id=str(reminder.id),
    ))


def sync_medication(db: Session, med: Medication, user_id: int) -> None:
    # Caller holds the medication row lock, as do schedule mutation and advancement.
    reminders = db.scalars(select(MedicationReminder).where(
        MedicationReminder.medication_id == med.id)).all()
    for reminder in reminders:
        clear_notifications(db, reminder.id)
        reminder.next_occurrence = next_due(med, reminder, datetime.now(UTC))
        enqueue(db, med, reminder, user_id)


def advance_due(db: Session, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    pending = list(db.execute(select(MedicationReminder.id, MedicationReminder.medication_id)
                             .where(MedicationReminder.next_occurrence <= now)
                             .order_by(MedicationReminder.next_occurrence).limit(100)))
    advanced = 0
    for reminder_id, medication_id in pending:
        locked = db.execute(update(Medication).where(Medication.id == medication_id)
                            .values(is_active=Medication.is_active)
                            .execution_options(synchronize_session=False))
        if locked.rowcount != 1:
            db.rollback()
            continue
        reminder = db.get(MedicationReminder, reminder_id, populate_existing=True)
        if reminder is None or reminder.next_occurrence is None:
            db.commit()
            continue
        due = reminder.next_occurrence.replace(tzinfo=reminder.next_occurrence.tzinfo or UTC)
        if due > now:
            db.commit()
            continue
        med = db.get(Medication, medication_id, populate_existing=True)
        patient = db.get(Patient, med.patient_id)
        reminder.next_occurrence = next_due(med, reminder, now)
        enqueue(db, med, reminder, patient.user_id)
        db.commit()
        advanced += 1
    return advanced


def obsolete(db: Session, notification: Notification, now: datetime) -> bool:
    reminder = db.get(MedicationReminder, int(notification.resource_id or "0"))
    if reminder is None or not reminder.is_enabled:
        return True
    med = db.get(Medication, reminder.medication_id)
    if med is None or not med.is_active or notification.scheduled_for is None:
        return True
    patient = db.get(Patient, med.patient_id)
    if patient is None or patient.user_id != notification.user_id:
        return True
    due = notification.scheduled_for.replace(tzinfo=notification.scheduled_for.tzinfo or UTC)
    day = now.astimezone(ZoneInfo(reminder.timezone)).date()
    # Do not send old medication reminders after outages or prolonged provider errors.
    return (now - due > timedelta(minutes=15)
            or bool(med.start_date and day < med.start_date)
            or bool(med.end_date and day > med.end_date))
