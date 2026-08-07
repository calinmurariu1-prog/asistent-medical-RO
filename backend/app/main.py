"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure all models are registered on Base.metadata.
import app.models  # noqa: F401,E402
from app.api.routes import api_router
from app.core.config import settings, validate_production_config

# Fail fast if deployed to production with insecure default secrets.
validate_production_config(settings)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description=(
        "Asistent Medical AI - API. Aceasta aplicatie NU pune diagnostice si "
        "NU inlocuieste consultul medical. Informatiile au caracter orientativ."
    ),
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def security_headers(request, call_next):
    """Baseline security headers on every response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(self), microphone=(), camera=()"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains"
        )
    return response

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.ENVIRONMENT}


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {
        "name": settings.PROJECT_NAME,
        "docs": "/docs",
        "disclaimer": (
            "Aplicatia ofera informatii orientative si nu inlocuieste "
            "sfatul medicului."
        ),
    }
