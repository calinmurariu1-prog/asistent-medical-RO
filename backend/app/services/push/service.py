"""Register device tokens and fan out push messages to a user's devices."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.push_token import PushToken
from app.models.user import User
from app.services.push.base import PushMessage
from app.services.push.factory import get_push_provider


def register_token(db: Session, user: User, token: str, platform: str) -> PushToken:
    """Idempotently register a device token for the user (re-homing if needed)."""
    row = db.scalar(select(PushToken).where(PushToken.token == token))
    if row is None:
        row = PushToken(user_id=user.id, token=token, platform=platform)
        db.add(row)
    else:
        row.user_id = user.id
        row.platform = platform
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def unregister_token(db: Session, user: User, token: str) -> None:
    row = db.scalar(select(PushToken).where(
        PushToken.token == token, PushToken.user_id == user.id))
    if row is not None:
        db.delete(row)
        db.commit()


def send_to_user(
    db: Session, user: User, title: str, body: str = "", data: dict | None = None
) -> dict[str, int]:
    """Separate simulated sends from provider acceptance; retain tokens on failures."""
    tokens = list(db.scalars(select(PushToken).where(PushToken.user_id == user.id)))
    result = {"delivered": 0, "simulated": 0, "failed": 0, "devices": len(tokens)}
    if not tokens:
        return result
    provider = get_push_provider()
    message = PushMessage(title=title, body=body, data=data or {})
    for token in tokens:
        if provider.send(token.token, message):
            result["simulated" if provider.name == "mock" else "delivered"] += 1
        else:
            # A timeout/credentials outage does not prove that the token expired.
            result["failed"] += 1
    return result


def send_notification(db: Session, notification: Notification) -> int:
    """Push an existing Notification row to the user's devices and mark it sent."""
    from app.models.enums import NotificationChannel, NotificationStatus

    if notification.channel != NotificationChannel.PUSH:
        return 0
    if notification.status in (NotificationStatus.SENT, NotificationStatus.READ):
        return 0
    scheduled = notification.scheduled_for
    if scheduled and scheduled.replace(tzinfo=scheduled.tzinfo or UTC) > datetime.now(UTC):
        return 0
    user = db.get(User, notification.user_id)
    if user is None:
        return 0
    delivered = send_to_user(
        db,
        user,
        "Asistent Medical",
        "Ai o notificare nouă. Deschide aplicația pentru detalii.",
        data={"notification_id": notification.id},
    )
    if delivered["delivered"]:
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.now(UTC)
        db.add(notification)
        db.commit()
    return delivered["delivered"]
