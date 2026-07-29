"""API route aggregation."""
from fastapi import APIRouter

from app.api.routes import auth, documents, labs, patients

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(patients.router)
api_router.include_router(documents.router)
api_router.include_router(labs.router)
