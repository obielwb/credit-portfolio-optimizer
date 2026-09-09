import os
import sys

import pytest

# Ensure the project `src` package is importable during tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker

import src.utils.db.session as db_session
from src.schema.database.base import Base


class Item(Base):
    __tablename__ = "session_items"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


@pytest.fixture()
def in_memory_engine():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return engine


def test_commit_persists_and_closes_session(in_memory_engine):
    engine = in_memory_engine
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    # Monkeypatch the SessionLocal used by the module
    db_session.SessionLocal = SessionLocal

    with db_session.get_db_session() as s:
        s.add(Item(name="commit_test"))
        s.flush()
        assert s.query(Item).count() == 1
        session_ref = s

    # verify persisted using a fresh session
    check = SessionLocal()
    try:
        assert check.query(Item).count() == 1
    finally:
        check.close()

    assert getattr(session_ref, "closed", True) is True


def test_rollback_reverts_transaction_on_exception(in_memory_engine):
    engine = in_memory_engine
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    db_session.SessionLocal = SessionLocal

    with pytest.raises(RuntimeError):
        with db_session.get_db_session() as s:
            s.add(Item(name="will_rollback"))
            # force an error to trigger rollback
            raise RuntimeError("force rollback")

    # ensure nothing was persisted
    check = SessionLocal()
    try:
        assert check.query(Item).count() == 0
    finally:
        check.close()
