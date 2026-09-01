"""Bază de date — SQLAlchemy 2, implicit SQLite (proiect izolat, zero-config)."""
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    # Importă modelele ca să fie înregistrate pe metadata înainte de create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
