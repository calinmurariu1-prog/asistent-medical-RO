"""API route aggregation."""
from fastapi import APIRouter

from app.api.routes import (
    admin,
    ai_skills,
    appointments,
    auth,
    chats,
    dashboard,
    documents,
    export,
    feedback,
    gdpr,
    health,
    history,
    labs,
    medications,
    monitoring,
    notifications,
    patients,
    providers,
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
api_router.include_router(providers.router)
api_router.include_router(gdpr.router)
api_router.include_router(health.router)
api_router.include_router(ai_skills.router)
api_router.include_router(export.router)
api_router.include_router(feedback.router)
api_router.include_router(admin.router)
