"""Tests do ComparisonRepository."""

from __future__ import annotations

import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import src.utils.db.session as db_session
from src.schema.database.base import Base
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


def _seed_run_with_context(*, status: str = "success", with_result: bool = True):
    from src.repositories import (
        CsvFileRepository,
        ClientRepository,
        ComparisonRepository,
        ParametersRepository,
        ResultRepository,
        RunRepository,
    )
    from src.schema.database.portfolio_results import PortfolioResults

    with get_db_session() as session:
        file_repo = CsvFileRepository(session)
        file = file_repo.create(
            file_repo.model(name="clients.csv", path_or_url="minio://test/clients.csv")
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
                enabled=True,
                n_clusters=None,
                max_clients_per_cluster=500,
                min_clusters=100,
                multipliers=[],
            )
        )

        run_repo = RunRepository(session)
        run = run_repo.create(
            run_repo.model(
                algorithm="simplex",
                execution_time_ms=1200,
                status=status,
                parameters_id=params.id,
                csv_file_id=file.id,
            )
        )

        if with_result:
            ResultRepository(session).create(
                PortfolioResults(
                    run_id=run.id,
                    total_clients=2,
                    total_limit=5000.0,
                    total_income=100.0,
                    total_loss=50.0,
                    total_return=200.0,
                    financial_default_rate=0.05,
                    baseline_default_rate=0.04,
                )
            )

        ClientRepository(session).create(
            ClientRepository(session).model(
                token="c1",
                last_run_id=run.id,
                last_suggested_limit=2500.0,
                payment_capacity=3000.0,
                score=0.8,
                pd=0.1,
            )
        )
        ClientRepository(session).create(
            ClientRepository(session).model(
                token="c2",
                last_run_id=run.id,
                last_suggested_limit=2500.0,
                payment_capacity=2800.0,
                score=0.7,
                pd=0.15,
            )
        )

        return run.id


def test_get_run_with_context_loads_relationships(in_memory_db):
    from src.repositories import ComparisonRepository

    run_id = _seed_run_with_context()

    with get_db_session() as session:
        repo = ComparisonRepository(session)
        run = repo.get_run_with_context(run_id)

        assert run is not None
        assert run.id == run_id
        assert run.algorithm == "simplex"
        assert run.file_csv is not None
        assert run.file_csv.name == "clients.csv"
        assert run.parameters is not None
        assert float(run.parameters.utilization_rate) == 0.7
        assert run.result is not None
        assert run.result.total_clients == 2


def test_get_run_with_context_returns_none_for_missing_run(in_memory_db):
    from src.repositories import ComparisonRepository

    with get_db_session() as session:
        repo = ComparisonRepository(session)
        assert repo.get_run_with_context(999) is None


def test_get_run_with_context_without_result(in_memory_db):
    from src.repositories import ComparisonRepository

    run_id = _seed_run_with_context(with_result=False)

    with get_db_session() as session:
        run = ComparisonRepository(session).get_run_with_context(run_id)
        assert run is not None
        assert run.result is None


def test_get_clients_by_run_returns_linked_clients(in_memory_db):
    from src.repositories import ComparisonRepository

    run_id = _seed_run_with_context()

    with get_db_session() as session:
        clients = ComparisonRepository(session).get_clients_by_run(run_id)
        assert len(clients) == 2
        assert {client.token for client in clients} == {"c1", "c2"}


def test_get_clients_by_run_returns_empty_for_unknown_run(in_memory_db):
    from src.repositories import ComparisonRepository

    _seed_run_with_context()

    with get_db_session() as session:
        assert ComparisonRepository(session).get_clients_by_run(999) == []
