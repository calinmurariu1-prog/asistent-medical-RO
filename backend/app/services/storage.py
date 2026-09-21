"""Object storage (MinIO / S3) service.

boto3 is imported lazily so the module can be imported in environments where
the dependency (or the storage backend) is not present — e.g. unit tests,
which override `get_storage` with an in-memory fake.
"""
from __future__ import annotations

import hashlib
import os
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.core.config import settings
from app.core.security import _fernet


class Storage(Protocol):
    """Minimal storage interface used by the app."""

    def put(self, key: str, data: bytes, content_type: str | None = None) -> None: ...

    def get(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...

    def presigned_url(self, key: str, expires: int = 3600) -> str: ...


def build_object_key(patient_id: int, filename: str) -> str:
    """Namespace objects per patient and add a random prefix to avoid clashes."""
    safe = filename.replace("/", "_").replace("\\", "_")
    return f"patients/{patient_id}/{uuid.uuid4().hex}_{safe}"


class S3Storage:
    """S3-compatible storage (works with AWS S3 and MinIO)."""

    def __init__(self) -> None:
        import boto3  # lazy

        self._bucket = settings.S3_BUCKET
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            use_ssl=settings.S3_USE_SSL,
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        from botocore.exceptions import ClientError

        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)

    def put(self, key: str, data: bytes, content_type: str | None = None) -> None:
        extra = {"ContentType": content_type} if content_type else {}
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data, **extra)

    def get(self, key: str) -> bytes:
        obj = self._client.get_object(Bucket=self._bucket, Key=key)
        return obj["Body"].read()

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def presigned_url(self, key: str, expires: int = 3600) -> str:
        url = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires,
        )
        # Rewrite internal endpoint to the browser-reachable public URL.
        if settings.S3_ENDPOINT_URL and settings.S3_PUBLIC_URL:
            url = url.replace(settings.S3_ENDPOINT_URL, settings.S3_PUBLIC_URL)
        return url


class LocalStorage:
    """Encrypted private files, never served as a static directory."""
    def __init__(self):
        self.root = Path(settings.LOCAL_DATA_DIR).resolve() / "originals"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.root / (hashlib.sha256(key.encode()).hexdigest() + ".enc")

    def put(self, key: str, data: bytes, content_type: str | None = None) -> None:
        target = self._path(key)
        temporary = target.with_suffix("." + uuid.uuid4().hex + ".tmp")
        try:
            temporary.write_bytes(_fernet().encrypt(data))
            temporary.chmod(0o600)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)

    def get(self, key: str) -> bytes:
        return _fernet().decrypt(self._path(key).read_bytes())

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def presigned_url(self, key: str, expires: int = 3600) -> str:
        raise ValueError("Local originals require an authenticated download")


@lru_cache
def _default_storage() -> Storage:
    if settings.STORAGE_BACKEND == "local" and not settings.is_production:
        return LocalStorage()
    if settings.STORAGE_BACKEND != "s3":
        raise RuntimeError("Unsupported storage configuration")
    return S3Storage()


def get_storage() -> Storage:
    return _default_storage()
