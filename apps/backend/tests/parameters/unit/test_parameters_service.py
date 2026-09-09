"""parameters_service validation tests."""

from __future__ import annotations

import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import src.utils.db.session as db_session
from src.models.parameters import MIN_CLUSTERS_FLOOR
from src.schema.database.base import Base
from src.services.parameters_service import update_active
from src.utils.db.bootstrap import default_parameters_values


@pytest.fixture()
def in_memory_db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    db_session.SessionLocal = SessionLocal
    yield


def _full_payload(**overrides) -> dict:
    payload = default_parameters_values()
    payload["multipliers"] = payload["multipliers"]
    payload.update(overrides)
    return payload


def test_update_active_persists_min_clusters(in_memory_db):
    created = update_active(_full_payload(min_clusters=150))

    assert created["min_clusters"] == 150


def test_update_active_rejects_min_clusters_below_minimum(in_memory_db):
    with pytest.raises(ValueError, match=f"min_clusters must be at least {MIN_CLUSTERS_FLOOR}"):
        update_active(_full_payload(min_clusters=99))


def test_update_active_accepts_min_clusters_at_minimum(in_memory_db):
    created = update_active(_full_payload(min_clusters=MIN_CLUSTERS_FLOOR))

    assert created["min_clusters"] == MIN_CLUSTERS_FLOOR
