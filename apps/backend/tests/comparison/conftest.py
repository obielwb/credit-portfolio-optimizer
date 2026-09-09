

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.utils.db.session as db_session
from src.schema.database.base import Base
from src.utils.db.session import get_db_session


@pytest.fixture()
def comparison_db():
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


def seed_comparable_run(
    *,
    with_result: bool = True,
    status: str = "success",
    total_limit: float = 5000.0,
    total_return: float = 200.0,
    file_name: str = "clients.csv",
    execution_time_ms: int = 1200,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
) -> int:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if started_at is None:
        started_at = now - timedelta(milliseconds=execution_time_ms)
    if finished_at is None:
        finished_at = now
    from src.repositories import (
        CsvFileRepository,
        ClientRepository,
        ParametersRepository,
        ResultRepository,
        RunRepository,
    )
    from src.schema.database.portfolio_results import PortfolioResults

    with get_db_session() as session:
        file = CsvFileRepository(session).create(
            CsvFileRepository(session).model(
                name=file_name,
                path_or_url=f"minio://test/{file_name}",
            )
        )

        params = ParametersRepository(session).create(
            ParametersRepository(session).model(
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

        run = RunRepository(session).create(
            RunRepository(session).model(
                algorithm="simplex",
                execution_time_ms=execution_time_ms,
                status=status,
                parameters_id=params.id,
                csv_file_id=file.id,
                started_at=started_at,
                finished_at=finished_at,
            )
        )

        if with_result:
            ResultRepository(session).create(
                PortfolioResults(
                    run_id=run.id,
                    total_clients=2,
                    total_limit=total_limit,
                    total_income=100.0,
                    total_loss=50.0,
                    total_return=total_return,
                    financial_default_rate=0.05,
                    baseline_default_rate=0.04,
                )
            )

        ClientRepository(session).create(
            ClientRepository(session).model(
                token=f"run{run.id}_c1",
                last_run_id=run.id,
                last_suggested_limit=2500.0,
                payment_capacity=3000.0,
                score=0.8,
                pd=0.10,
            )
        )
        ClientRepository(session).create(
            ClientRepository(session).model(
                token=f"run{run.id}_c2",
                last_run_id=run.id,
                last_suggested_limit=0.0,
                payment_capacity=2800.0,
                score=0.7,
                pd=0.20,
            )
        )

        return run.id


def seed_run_clusters(run_id: int) -> None:
    from src.repositories import RunClusterRepository

    with get_db_session() as session:
        repo = RunClusterRepository(session)
        RunClusters = repo.model
        for cluster_id, total_clients, average_capacity in (
            (1, 100, 10000.0),
            (2, 50, 8000.0),
        ):
            repo.create(
                RunClusters(
                    run_id=run_id,
                    cluster_id=cluster_id,
                    total_clients=total_clients,
                    average_pd=0.1,
                    average_score=0.5,
                    average_capacity=average_capacity,
                    policy_name="default",
                    leverage_multiplier=0.3,
                )
            )
