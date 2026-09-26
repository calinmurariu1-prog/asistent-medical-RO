from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.user import User
from app.services.mfa_recovery import consume, issue


def _concurrent(engine):
    with Session(engine) as db:
        user = User(email="backup-concurrent@example.com", hashed_password="synthetic")
        db.add(user)
        db.flush()
        user_id = user.id
        code = issue(db, user_id)[0]
        db.commit()

    def use(_):
        with Session(engine) as db:
            accepted = consume(db, user_id, code)
            db.commit()
            return accepted

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(use, range(2))) == [False, True]


def test_atomic_backup_consumption_sqlite(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "backup.db"),
                           connect_args={"timeout": 20})
    try:
        Base.metadata.create_all(engine)
        _concurrent(engine)
    finally:
        engine.dispose()


def test_atomic_backup_consumption_postgres(db_session):
    engine = db_session.get_bind()
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL concurrency runs in CI")
    _concurrent(engine)


def test_backup_consumption_is_owner_scoped_and_rolls_back(db_session):
    user = User(email="backup-owner@example.com", hashed_password="synthetic")
    db_session.add(user)
    db_session.flush()
    user_id = user.id
    code = issue(db_session, user_id)[0]
    db_session.commit()
    assert consume(db_session, user_id + 1, code) is False
    assert consume(db_session, user_id, code) is True
    db_session.rollback()
    assert consume(db_session, user_id, code) is True
    db_session.commit()
    assert consume(db_session, user_id, code) is False
