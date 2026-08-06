"""Module 15 - user feedback submission."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.feedback import Feedback
from app.models.user import User
from app.schemas.admin import FeedbackCreate, FeedbackOut

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: FeedbackCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Feedback:
    fb = Feedback(user_id=user.id, message=payload.message, rating=payload.rating)
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb
