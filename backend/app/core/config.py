"""Application configuration, loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ---- General ----
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "Asistent Medical AI"
    API_V1_PREFIX: str = "/api/v1"
    # NoDecode: keep pydantic-settings from JSON-decoding the env value so the
    # validator below can accept a plain comma-separated string.
    BACKEND_CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(default_factory=list)

    # ---- Security ----
    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DATA_ENCRYPTION_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"

    # ---- Rate limiting ----
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN_TIMES: int = 10
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # ---- Database ----
    DATABASE_URL: str = (
        "postgresql+psycopg://medai:medai_dev_password@db:5432/asistent_medical"
    )

    # ---- Object storage ----
    S3_ENDPOINT_URL: str = "http://minio:9000"
    S3_PUBLIC_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "medical-documents"
    S3_REGION: str = "eu-central-1"
    S3_USE_SSL: bool = False

    # ---- AI ----
    AI_DEFAULT_PROVIDER: str = "anthropic"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-5"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-pro"

    # MedLLM micro-service (z-ai CLI wrapper). No API key needed here; the
    # micro-service handles credentials. Reachable by service name in Docker.
    MED_LLM_URL: str = "http://med-llm:3031"
    MED_LLM_TIMEOUT: float = 90.0
    # If the micro-service is unreachable, fall back to the offline mock instead
    # of returning the disclaimer for every call (smoother dev experience).
    MED_LLM_FALLBACK_MOCK: bool = True
    MED_LLM_HEALTH_TTL: float = 30.0

    # ---- Maps / provider search (Google Places) ----
    # Server-side key (IP-restricted). Never exposed to the browser.
    GOOGLE_MAPS_API_KEY: str = ""
    PLACES_DEFAULT_RADIUS_M: int = 5000
    PLACES_MAX_RESULTS: int = 10

    # ---- OCR ----
    OCR_LANGUAGES: str = "ron+eng"

    # ---- OAuth ----
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    APPLE_CLIENT_ID: str = ""

    # ---- Email ----
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@asistent-medical.ro"
    SMTP_TLS: bool = True
    FRONTEND_URL: str = "http://localhost:3000"

    # ---- Consent enforcement ----
    # When true, AI features require an active AI_PROCESSING consent.
    REQUIRE_AI_CONSENT: bool = False

    # ---- In-App Purchase (mobile subscriptions) ----
    # Product IDs configured in the stores, mapped to plans:
    #   "<product_id>:<plan>,<product_id>:<plan>"  (plan = premium|family)
    IAP_PRODUCTS: str = (
        "premium_monthly:premium,family_monthly:family"
    )
    # Allow the deterministic mock verifier (dev/test). Disabled in production
    # unless explicitly turned on.
    IAP_ALLOW_MOCK: bool = True

    # Apple App Store Server API (JWT signed with an App Store Connect key).
    APPLE_IAP_BUNDLE_ID: str = ""
    APPLE_IAP_ISSUER_ID: str = ""
    APPLE_IAP_KEY_ID: str = ""
    APPLE_IAP_PRIVATE_KEY: str = ""          # PEM contents of the .p8 key
    APPLE_IAP_ENVIRONMENT: str = "production"  # or "sandbox"

    # Google Play Developer API (service-account credentials).
    GOOGLE_PLAY_PACKAGE_NAME: str = ""
    GOOGLE_PLAY_SERVICE_ACCOUNT_JSON: str = ""  # raw JSON of the SA key

    # ---- Stripe (web subscriptions) ----
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    # plan -> Stripe Price ID: "premium:price_xxx,family:price_yyy"
    STRIPE_PRICES: str = ""
    STRIPE_SUCCESS_URL: str = ""   # defaults to FRONTEND_URL + /subscription?status=success
    STRIPE_CANCEL_URL: str = ""    # defaults to FRONTEND_URL + /subscription?status=cancel
    STRIPE_PORTAL_RETURN_URL: str = ""  # defaults to FRONTEND_URL + /subscription
    # Allow the mock gateway (dev/test) when no secret key is set.
    STRIPE_ALLOW_MOCK: bool = True

    # ---- Push notifications (Firebase Cloud Messaging) ----
    FCM_PROJECT_ID: str = ""
    FCM_SERVICE_ACCOUNT_JSON: str = ""  # raw JSON of the SA key
    # Allow the mock sender (dev/test) when FCM isn't configured.
    PUSH_ALLOW_MOCK: bool = True

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        # Managed hosts (Render/Heroku) hand out `postgres://` / `postgresql://`
        # URLs; SQLAlchemy needs the psycopg-v3 driver spelled out.
        for prefix in ("postgresql://", "postgres://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        if isinstance(v, list):
            return v
        return []

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    # Origins used by the Capacitor native WebView (Android/iOS). Always allowed
    # since they're only reachable from inside the app, never a remote site.
    MOBILE_CORS_ORIGINS: tuple[str, ...] = (
        "capacitor://localhost",
        "ionic://localhost",
        "http://localhost",
        "https://localhost",
    )

    @property
    def cors_origins(self) -> list[str]:
        """Configured web origins + the fixed mobile WebView origins."""
        merged = list(self.BACKEND_CORS_ORIGINS)
        for origin in self.MOBILE_CORS_ORIGINS:
            if origin not in merged:
                merged.append(origin)
        return merged


def validate_production_config(s: Settings) -> None:
    """Refuse to run in production with insecure default secrets."""
    if not s.is_production:
        return
    problems: list[str] = []
    if s.SECRET_KEY.startswith("change-me") or len(s.SECRET_KEY) < 32:
        problems.append("SECRET_KEY")
    if not s.DATA_ENCRYPTION_KEY or s.DATA_ENCRYPTION_KEY.startswith("change-me"):
        problems.append("DATA_ENCRYPTION_KEY")
    if problems:
        raise RuntimeError(
            "Configurare nesigură pentru producție — setează valori reale pentru: "
            + ", ".join(problems)
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
