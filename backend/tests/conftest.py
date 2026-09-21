"""Pytest fixtures: an isolated SQLite-backed app + client."""
from __future__ import annotations

import os
import tempfile
from uuid import uuid4

os.environ.setdefault("DATA_ENCRYPTION_KEY", "test-encryption-key-please-change-000")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ["STORAGE_CLEANUP_ENABLED"] = "false"
os.environ["LOCAL_DATA_DIR"] = tempfile.mkdtemp(prefix="medical-ro-tests-")
# Keep the shared in-process rate limiter from tripping across the suite; the
# dedicated rate-limit test re-enables it explicitly.
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (register tables before app.main rebinds `app`)
from app.core.database import Base, get_db
from app.main import app  # noqa: E402  (`app` here is the FastAPI instance)
from app.services.storage import get_storage


class InMemoryStorage:
    """Test double for the S3/MinIO storage backend."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def put(self, key: str, data: bytes, content_type: str | None = None) -> None:
        self._objects[key] = data

    def get(self, key: str) -> bytes:
        return self._objects[key]

    def delete(self, key: str) -> None:
        self._objects.pop(key, None)

    def presigned_url(self, key: str, expires: int = 3600) -> str:
        return f"https://storage.test/{key}?expires={expires}"


@pytest.fixture()
def db_session():
    postgres_url = os.environ.get("TEST_POSTGRES_URL")
    schema = None
    admin_engine = None
    if postgres_url:
        url = make_url(postgres_url)
        if (url.get_backend_name() != "postgresql" or url.host not in {"localhost", "127.0.0.1"}
                or url.database != "medical_ro_ci"):
            raise RuntimeError("PostgreSQL tests require the isolated local medical_ro_ci database")
        schema = "test_" + uuid4().hex
        admin_engine = create_engine(postgres_url)
        with admin_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_engine(postgres_url, connect_args={"options": f"-csearch_path={schema}"})
    else:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        if admin_engine is not None:
            engine.dispose()
            with admin_engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin_engine.dispose()
        else:
            Base.metadata.drop_all(engine)
            engine.dispose()


@pytest.fixture()
def storage():
    return InMemoryStorage()


@pytest.fixture()
def client(db_session, storage):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_storage] = lambda: storage
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
