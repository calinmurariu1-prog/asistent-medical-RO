import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base
from app.models.user import RecoveryToken, User
from app.services.email import send_email
from app.services.storage import LocalStorage
from app.services.token_service import PASSWORD_RESET, consume_purpose_token, create_purpose_token

API = "/api/v1"


def make_user(client):
    return client.post(API + "/auth/register", json={
        "email": "recovery@example.com", "password": "Password1234"
    }).json()["id"]


def test_reset_tokens_are_one_use_and_purpose_bound(client, db_session):
    uid = make_user(client)
    token = create_purpose_token(str(uid), PASSWORD_RESET, db=db_session)
    db_session.commit()
    assert token not in str(db_session.scalars(select(RecoveryToken.token_hash)).all())
    assert client.post(API + "/auth/email/verify", json={"token": token}).status_code == 400
    body = {"token": token, "new_password": "NewPassword1234"}
    assert client.post(API + "/auth/password-reset/confirm", json=body).status_code == 200
    assert client.post(API + "/auth/password-reset/confirm", json=body).status_code == 400
    assert client.post(API + "/auth/login", json={
        "email": "recovery@example.com", "password": "Password1234"
    }).status_code == 401


def test_expired_reset(client, db_session):
    uid = make_user(client)
    token = create_purpose_token(str(uid), PASSWORD_RESET, db=db_session)
    row = db_session.get(RecoveryToken, hashlib.sha256(token.encode()).hexdigest())
    row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()
    assert client.post(API + "/auth/password-reset/confirm", json={
        "token": token, "new_password": "NewPassword1234"
    }).status_code == 400


def test_concurrent_token_consumption(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "concurrency.db"),
                           connect_args={"timeout": 20})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(email="parallel@example.com", hashed_password="test")
        db.add(user)
        db.flush()
        token = create_purpose_token(str(user.id), PASSWORD_RESET, db=db)
        db.commit()
    def consume(_):
        with Session(engine) as db:
            user = consume_purpose_token(token, PASSWORD_RESET, db)
            if user:
                user.token_version += 1
            db.commit()
            return user is not None
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(consume, range(2))) == [False, True]
    engine.dispose()


def test_mailbox_no_token_in_logs(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(settings, "LOCAL_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    with caplog.at_level(logging.INFO):
        assert send_email("fake@example.com", "Reset", "secret-reset-token")
    assert "secret-reset-token" not in caplog.text
    assert "secret-reset-token" in next((tmp_path / "mailbox").glob("*.txt")).read_text()


def test_production_without_smtp_is_uniform(client, monkeypatch):
    make_user(client)
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    for email in ["recovery@example.com", "missing@example.com"]:
        assert client.post(API + "/auth/password-reset/request",
                           json={"email": email}).status_code == 503


def test_local_original_is_encrypted_and_persistent(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "LOCAL_DATA_DIR", str(tmp_path))
    storage = LocalStorage()
    storage.put("../../private", b"original fictiv")
    assert b"original fictiv" not in next((tmp_path / "originals").iterdir()).read_bytes()
    assert LocalStorage().get("../../private") == b"original fictiv"
    storage.delete("../../private")
    assert list((tmp_path / "originals").iterdir()) == []


def test_postgres_concurrent_token_consumption(db_session):
    engine = db_session.get_bind()
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL concurrency is verified in the isolated CI service")
    user = User(email="postgres-parallel@example.com", hashed_password="test-only")
    db_session.add(user)
    db_session.flush()
    token = create_purpose_token(str(user.id), PASSWORD_RESET, db=db_session)
    db_session.commit()

    def consume(_):
        with Session(engine) as db:
            account = consume_purpose_token(token, PASSWORD_RESET, db)
            if account:
                account.token_version += 1
            db.commit()
            return account is not None

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(consume, range(2))) == [False, True]
    db_session.refresh(user)
    assert user.token_version == 1


def test_resend_verification_is_authenticated_private_and_recoverable(client, monkeypatch):
    from app.api.routes import auth

    make_user(client)
    token = client.post(API + "/auth/login", json={
        "email": "recovery@example.com", "password": "Password1234"}).json()["access_token"]
    headers = {"Authorization": "Bearer " + token}
    assert client.post(API + "/auth/email/resend").status_code == 401
    sent = []
    monkeypatch.setattr(auth, "send_verification_email", lambda email, code: sent.append(
        (email, code)) or True)
    response = client.post(API + "/auth/email/resend", headers=headers)
    assert response.status_code == 200
    assert sent[0][0] == "recovery@example.com"
    assert sent[0][1] not in response.text
    monkeypatch.setattr(auth, "send_verification_email", lambda *args: False)
    assert client.post(API + "/auth/email/resend", headers=headers).status_code == 503
    assert client.post(API + "/auth/email/verify", json={"token": sent[0][1]}).status_code == 200
    response = client.post(API + "/auth/email/resend", headers=headers)
    assert response.status_code == 200
    assert "deja confirmată" in response.json()["detail"]
