from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import settings
from app.models.user import RecoveryToken, User
from app.services.token_service import EMAIL_VERIFY, PASSWORD_RESET, purge_expired


def test_expired_token_retention_is_bounded_and_preserves_live_and_unknown_purposes(
    db_session, monkeypatch,
):
    monkeypatch.setattr(settings, "RECOVERY_TOKEN_RETENTION_HOURS", 24)
    now = datetime.now(UTC)
    user = User(email="retention@example.com", hashed_password="synthetic")
    db_session.add(user)
    db_session.flush()
    cases = [
        ("a", PASSWORD_RESET, -48, None),
        ("b", EMAIL_VERIFY, -24, now),
        ("c", PASSWORD_RESET, -23, None),
        ("d", EMAIL_VERIFY, 2, now),
        ("e", "unknown-purpose", -48, None),
    ]
    db_session.add_all(RecoveryToken(token_hash=key * 64, user_id=user.id, purpose=purpose,
                      expires_at=now + timedelta(hours=hours), consumed_at=consumed)
                      for key, purpose, hours, consumed in cases)
    db_session.commit()
    assert purge_expired(db_session, now=now, batch_size=1) == 1
    assert purge_expired(db_session, now=now, batch_size=1) == 1
    assert purge_expired(db_session, now=now, batch_size=1) == 0
    remaining = set(db_session.scalars(select(RecoveryToken.token_hash)))
    assert remaining == {"c" * 64, "d" * 64, "e" * 64}
    assert db_session.get(User, user.id) is not None


def test_cleanup_worker_purges_tokens_even_without_storage_jobs(db_session, monkeypatch):
    from contextlib import nullcontext

    from app.services import storage_cleanup

    user = User(email="worker-retention@example.com", hashed_password="synthetic")
    db_session.add(user)
    db_session.flush()
    db_session.add(RecoveryToken(token_hash="f" * 64, user_id=user.id, purpose=PASSWORD_RESET,
                                expires_at=datetime.now(UTC) - timedelta(days=400)))
    db_session.commit()
    monkeypatch.setattr(storage_cleanup, "SessionLocal", lambda: nullcontext(db_session))
    storage_cleanup.run_batch()
    assert db_session.get(RecoveryToken, "f" * 64) is None
