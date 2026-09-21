"""Durable push outbox. Provider acceptance is not proof of device display."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus, NotificationChannel, NotificationStatus
from app.models.notification import Notification
from app.models.push_token import PushToken
from app.models.user import User
from app.services.push.base import PushMessage, PushProvider
from app.services.push.factory import get_push_provider

logger = logging.getLogger(__name__)


def _available(now: datetime):
    return (
        Notification.status == NotificationStatus.PENDING,
        Notification.channel == NotificationChannel.PUSH,
        or_(Notification.scheduled_for.is_(None), Notification.scheduled_for <= now),
        or_(Notification.next_delivery_at.is_(None), Notification.next_delivery_at <= now),
        or_(Notification.delivery_until.is_(None), Notification.delivery_until < now),
    )


def process_due(db: Session, provider: PushProvider | None = None) -> int:
    now = datetime.now(UTC)
    ids = list(db.scalars(select(Notification.id).where(*_available(now))
                         .order_by(Notification.created_at).limit(25)))
    if not ids:
        return 0
    provider = provider or get_push_provider()
    if provider.name == "mock":
        return 0  # In-app items remain available; never fabricate external delivery.
    completed = 0
    for notification_id in ids:
        claimed_at = datetime.now(UTC)
        token = str(uuid.uuid4())
        claimed = db.execute(update(Notification).where(
            Notification.id == notification_id, *_available(claimed_at),
        ).values(delivery_token=token, delivery_until=claimed_at + timedelta(minutes=5),
                 delivery_attempts=Notification.delivery_attempts + 1)
            .execution_options(synchronize_session=False))
        db.commit()
        if claimed.rowcount != 1:
            continue
        notification = db.get(Notification, notification_id, populate_existing=True)
        if notification is None:
            continue
        attempts = notification.delivery_attempts
        delivered = False
        obsolete = False
        try:
            user = db.get(User, notification.user_id)
            obsolete = user is None or not user.is_active
            if notification.resource_type == "appointment":
                appointment = db.get(Appointment, int(notification.resource_id or "0"))
                obsolete = obsolete or appointment is None
                if appointment:
                    starts = appointment.starts_at.replace(
                        tzinfo=appointment.starts_at.tzinfo or UTC)
                    obsolete = obsolete or appointment.status != AppointmentStatus.SCHEDULED
                    obsolete = obsolete or starts <= datetime.now(UTC)
            if not obsolete:
                devices = list(db.scalars(select(PushToken).where(
                    PushToken.user_id == notification.user_id)))
                for device in devices:
                    # Renew and fence before each network request. Cancellation clears the token.
                    renewed = db.execute(update(Notification).where(
                        Notification.id == notification_id, Notification.delivery_token == token,
                        Notification.status == NotificationStatus.PENDING,
                    ).values(delivery_until=datetime.now(UTC) + timedelta(minutes=5))
                        .execution_options(synchronize_session=False))
                    db.commit()
                    if renewed.rowcount != 1:
                        break
                    delivered = provider.send(device.token, PushMessage(
                        title="Asistent Medical",
                        body="Ai o notificare nouă. Deschide aplicația pentru detalii.",
                        data={"notification_id": notification_id},
                    )) or delivered
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            logger.warning("Notification delivery deferred (%s)", type(exc).__name__)
        retry_minutes = min(60, 2 ** min(attempts, 6))
        values = {"delivery_token": None, "delivery_until": None,
                  "next_delivery_at": datetime.now(UTC) + timedelta(minutes=retry_minutes)}
        if obsolete:
            values["status"] = NotificationStatus.FAILED
        elif delivered:
            values.update(status=NotificationStatus.SENT, sent_at=datetime.now(UTC),
                          next_delivery_at=None)
        finished = db.execute(update(Notification).where(
            Notification.id == notification_id, Notification.delivery_token == token,
            Notification.status == NotificationStatus.PENDING,
        ).values(**values).execution_options(synchronize_session=False))
        db.commit()
        completed += int(delivered and finished.rowcount == 1)
    return completed


def run_batch() -> None:
    with SessionLocal() as db:
        process_due(db)


async def worker(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            await asyncio.to_thread(run_batch)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Notification worker deferred (%s)", type(exc).__name__)
        try:
            await asyncio.wait_for(stop.wait(), timeout=settings.NOTIFICATION_INTERVAL_SECONDS)
        except TimeoutError:
            pass
