"""Module 14 - notifications (push / email / SMS).

Creation and lifecycle live here. Actual delivery is abstracted behind
`_dispatch`, which currently logs and marks the notification sent. Real
channel adapters (FCM/APNs push, SMTP email, SMS gateway) and a scheduler for
future-dated reminders plug in here without touching the API.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.enums import (
    AppointmentStatus,
    NotificationChannel,
    NotificationStatus,
)
from app.models.notification import Notification

logger = logging.getLogger(__name__)


def _dispatch(db: Session, notification: Notification) -> None:
    """Send now if due; otherwise leave PENDING for the scheduler."""
    now = datetime.now(UTC)
    if notification.scheduled_for and notification.scheduled_for > now:
        notification.status = NotificationStatus.PENDING
        return
    # TODO: route to the real channel adapter based on notification.channel.
    logger.info(
        "Dispatching %s notification to user %s: %s",
        notification.channel.value,
        notification.user_id,
        notification.title,
    )
    notification.status = NotificationStatus.SENT
    notification.sent_at = now


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
    _dispatch(db, notification)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def list_notifications(
    db: Session, user_id: int, *, unread_only: bool = False
) -> list[Notification]:
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.status != NotificationStatus.READ)
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


def generate_appointment_reminders(
    db: Session, *, user_id: int, patient_id: int
) -> list[Notification]:
    """Create a reminder for each upcoming scheduled appointment without one."""
    now = datetime.now(UTC)
    appts = db.scalars(
        select(Appointment).where(
            Appointment.patient_id == patient_id,
            Appointment.starts_at >= now,
            Appointment.status == AppointmentStatus.SCHEDULED,
        )
    ).all()

    existing = {
        n.resource_id
        for n in list_notifications(db, user_id)
        if n.resource_type == "appointment"
    }

    created: list[Notification] = []
    for appt in appts:
        if str(appt.id) in existing:
            continue
        created.append(
            create_notification(
                db,
                user_id=user_id,
                title=f"Programare: {appt.title}",
                body=f"Ai o programare pe {appt.starts_at:%d.%m.%Y %H:%M}.",
                resource_type="appointment",
                resource_id=appt.id,
            )
        )
    return created
