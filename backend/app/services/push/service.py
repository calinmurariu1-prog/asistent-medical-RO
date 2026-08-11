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


def unregister_token(db: Session, token: str) -> None:
    row = db.scalar(select(PushToken).where(PushToken.token == token))
    if row is not None:
        db.delete(row)
        db.commit()


def send_to_user(
    db: Session, user: User, title: str, body: str = "", data: dict | None = None
) -> int:
    """Send a push to all of the user's devices; prune tokens that fail.

    Returns the number of devices reached.
    """
    tokens = list(
        db.scalars(select(PushToken).where(PushToken.user_id == user.id)).all()
    )
    if not tokens:
        return 0
    provider = get_push_provider()
    message = PushMessage(title=title, body=body, data=data or {})
    delivered = 0
    for t in tokens:
        if provider.send(t.token, message):
            delivered += 1
        else:
            # Failed/expired token — drop it so we stop trying.
            db.delete(t)
    db.commit()
    return delivered


def send_notification(db: Session, notification: Notification) -> int:
    """Push an existing Notification row to the user's devices and mark it sent."""
    from app.models.enums import NotificationStatus

    user = db.get(User, notification.user_id)
    if user is None:
        return 0
    delivered = send_to_user(
        db,
        user,
        notification.title,
        notification.body or "",
        data={"notification_id": notification.id},
    )
    if delivered:
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.now(UTC)
        db.add(notification)
        db.commit()
    return delivered
