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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
