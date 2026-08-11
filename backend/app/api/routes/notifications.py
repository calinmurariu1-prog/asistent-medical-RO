"""Module 14 - Notifications."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_patient, get_current_user
from app.core.database import get_db
from app.models.notification import Notification
from app.models.patient import Patient
from app.models.user import User
from app.schemas.notification import NotificationCreate, NotificationOut
from app.services import notification_service
from app.services.push import service as push_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


class PushTokenIn(BaseModel):
    token: str
    platform: str = "android"  # ios | android | web


@router.post("/push-token", status_code=status.HTTP_204_NO_CONTENT)
def register_push_token(
    payload: PushTokenIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Register this device's push token (called by the mobile app on launch)."""
    push_service.register_token(db, user, payload.token.strip(), payload.platform)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/push-token", status_code=status.HTTP_204_NO_CONTENT)
def delete_push_token(
    payload: PushTokenIn,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    push_service.unregister_token(db, payload.token.strip())
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/test-push", response_model=dict[str, int])
def send_test_push(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    """Send a test push to the user's registered devices."""
    delivered = push_service.send_to_user(
        db, user, "Asistent Medical AI", "Notificările push funcționează! 🎉"
    )
    return {"delivered": delivered}


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Notification]:
    return notification_service.list_notifications(db, user.id, unread_only=unread_only)


@router.post("", response_model=NotificationOut, status_code=status.HTTP_201_CREATED)
def create_notification(
    payload: NotificationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Notification:
    return notification_service.create_notification(
        db,
        user_id=user.id,
        title=payload.title,
        body=payload.body,
        channel=payload.channel,
        scheduled_for=payload.scheduled_for,
    )


@router.post("/reminders/appointments", response_model=list[NotificationOut])
def generate_appointment_reminders(
    user: User = Depends(get_current_user),
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> list[Notification]:
    reminders = notification_service.generate_appointment_reminders(
        db, user_id=user.id, patient_id=patient.id
    )
    # Best-effort push for each new reminder (no-op if no devices registered).
    for reminder in reminders:
        push_service.send_notification(db, reminder)
    return reminders


@router.post("/read-all", response_model=dict[str, int])
def mark_all_read(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    return {"marked_read": notification_service.mark_all_read(db, user.id)}


def _owned(notification_id: int, user: User, db: Session) -> Notification:
    n = db.get(Notification, notification_id)
    if n is None or n.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notificare inexistentă")
    return n


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Notification:
    return notification_service.mark_read(db, _owned(notification_id, user, db))


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    db.delete(_owned(notification_id, user, db))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
