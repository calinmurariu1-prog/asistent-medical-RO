"""Persist in-app notifications; only a real adapter can confirm external sending."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.enums import (
    AppointmentStatus,
    NotificationChannel,
    NotificationStatus,
)
from app.models.notification import Notification


def create_notification(
    db: Session,
    *,
    user_id: int,
    title: str,
    body: str | None = None,
    channel: NotificationChannel = NotificationChannel.PUSH,
    scheduled_for: datetime | None = None,
    resource_type: str | None = None,
    resource_id: str | int | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        channel=channel,
        title=title,
        body=body,
        scheduled_for=scheduled_for,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
    )
    notification.status = NotificationStatus.PENDING
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def list_notifications(
    db: Session, user_id: int, *, unread_only: bool = False
) -> list[Notification]:
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.status != NotificationStatus.READ,
                          or_(Notification.scheduled_for.is_(None),
                              Notification.scheduled_for <= datetime.now(UTC)))
    return list(db.scalars(stmt.order_by(Notification.created_at.desc())).all())


def mark_read(db: Session, notification: Notification) -> Notification:
    notification.status = NotificationStatus.READ
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_read(db: Session, user_id: int) -> int:
    items = list_notifications(db, user_id, unread_only=True)
    for n in items:
        n.status = NotificationStatus.READ
        db.add(n)
    db.commit()
    return len(items)


def sync_appointment_reminder(db: Session, *, user_id: int, appointment: Appointment) -> None:
    """Called within the appointment transaction; edits cancel pending claims."""
    db.execute(delete(Notification).where(
        Notification.user_id == user_id, Notification.resource_type == "appointment",
        Notification.resource_id == str(appointment.id),
    ))
    now = datetime.now(UTC)
    starts = appointment.starts_at.replace(tzinfo=appointment.starts_at.tzinfo or UTC)
    if appointment.status != AppointmentStatus.SCHEDULED or starts <= now:
        return
    db.add(Notification(
        user_id=user_id, channel=NotificationChannel.PUSH,
        title=f"Programare: {appointment.title}"[:300],
        body=f"Ai o programare pe {starts.astimezone(UTC):%d.%m.%Y %H:%M} UTC.",
        status=NotificationStatus.PENDING, scheduled_for=max(now, starts - timedelta(hours=24)),
        resource_type="appointment", resource_id=str(appointment.id),
    ))


def generate_appointment_reminders(
    db: Session, *, user_id: int, patient_id: int
) -> list[Notification]:
    """Backfill missing reminders for legacy appointments, serialized per appointment."""
    now = datetime.now(UTC)
    ids = list(db.scalars(select(Appointment.id).where(
        Appointment.patient_id == patient_id, Appointment.starts_at >= now,
        Appointment.status == AppointmentStatus.SCHEDULED,
    )))
    created = []
    for appointment_id in ids:
        locked = db.execute(update(Appointment).where(
            Appointment.id == appointment_id, Appointment.patient_id == patient_id,
        ).values(status=Appointment.status).execution_options(synchronize_session=False))
        if locked.rowcount != 1:
            continue
        appointment = db.get(Appointment, appointment_id, populate_existing=True)
        existing = db.scalar(select(Notification.id).where(
            Notification.user_id == user_id, Notification.resource_type == "appointment",
            Notification.resource_id == str(appointment_id),
        ))
        if existing is None:
            sync_appointment_reminder(db, user_id=user_id, appointment=appointment)
            db.flush()
            reminder = db.scalar(select(Notification).where(
                Notification.user_id == user_id, Notification.resource_type == "appointment",
                Notification.resource_id == str(appointment_id),
            ))
            if reminder:
                created.append(reminder)
        db.commit()
    return created
