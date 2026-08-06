"""API route aggregation."""
from fastapi import APIRouter

from app.api.routes import (
    appointments,
    auth,
    chats,
    dashboard,
    documents,
    history,
    labs,
    medications,
    monitoring,
    notifications,
    patients,
    recommendations,
    timeline,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(patients.router)
api_router.include_router(documents.router)
api_router.include_router(labs.router)
api_router.include_router(chats.router)
api_router.include_router(medications.router)
api_router.include_router(monitoring.router)
api_router.include_router(appointments.router)
api_router.include_router(notifications.router)
api_router.include_router(history.router)
api_router.include_router(timeline.router)
api_router.include_router(recommendations.router)
api_router.include_router(dashboard.router)
