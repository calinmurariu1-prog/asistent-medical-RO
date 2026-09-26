"""Database engine, session factory and declarative base."""
from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from sqlite3 import Connection as SQLiteConnection

from sqlalchemy import DateTime, create_engine, event, func
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
)

from app.core.config import settings


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(connection, _record):
    if isinstance(connection, SQLiteConnection):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
)


class Base(DeclarativeBase):
    """Declarative base with created/updated timestamp mixins available."""


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


def get_db() -> Generator:
    """FastAPI dependency that yields a scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
