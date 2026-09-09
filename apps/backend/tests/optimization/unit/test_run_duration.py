"""Run-duration calculation tests."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import src.utils.db.session as db_session
from src.repositories import CsvFileRepository, ParametersRepository, RunRepository
from src.schema.database.base import Base
from src.services.optimization_service import _compute_run_duration_ms, complete_run
from src.utils.db.session import get_db_session


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


def _seed_run(in_memory_db, *, started_at: datetime | None = None) -> int:
    with get_db_session() as session:
        file = CsvFileRepository(session).create(
            CsvFileRepository(session).model(
                name="test.csv",
                path_or_url="minio://test/test.csv",
            )
        )
        params_repo = ParametersRepository(session)
        params = params_repo.create(
            params_repo.model(
                utilization_rate=0.7,
                lgd=0.8,
                min_pd=0.0,
                max_pd=1.0,
                filter=False,
                max_limit=25000.0,
                baseline_default_rate=0.05,
                min_limit=200.0,
                discretize=False,
                interchange=0.0175,
                max_rejected_limit=25000.0,
                enabled=False,
                n_clusters=None,
                max_clients_per_cluster=100,
                min_clusters=100,
                multipliers={},
            )
        )
        run = RunRepository(session).create(
            RunRepository(session).model(
                algorithm="simplex",
                execution_time_ms=0,
                status="pending",
                parameters_id=params.id,
                csv_file_id=file.id,
                started_at=started_at,
            )
        )
        return run.id


def test_compute_run_duration_ms_from_started_at(in_memory_db):
    started = datetime.now(timezone.utc) - timedelta(seconds=3)
    with get_db_session() as session:
        run = RunRepository(session).get_by_id(_seed_run(in_memory_db, started_at=started))
        time = _compute_run_duration_ms(run)
    assert time >= 2500


def test_complete_run_persists_duration(in_memory_db):
    started = datetime.now(timezone.utc) - timedelta(seconds=2)
    run_id = _seed_run(in_memory_db, started_at=started)

    complete_run(
        run_id,
        {
            "result_portfolio": {
                "total_clients": 0,
                "total_limit": 0,
                "total_income": 0,
                "total_loss": 0,
                "total_return": 0,
                "financial_default_rate": 0,
                "baseline_default_rate": 0,
                "clients": [],
            },
            "clusters": [],
        },
    )

    with get_db_session() as session:
        run = RunRepository(session).get_by_id(run_id)
        assert run.execution_time_ms >= 1500
