import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.utils.db.session as db_session
from src.models.client import OptimizationClient
from src.repositories import (
    CsvFileRepository,
    ClientRepository,
    ParametersRepository,
    RunRepository,
)
from src.schema import OptimizationJobSchema
from src.schema.database.base import Base
from src.services.client_pipeline_input import load_clients_for_job
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


def _seed_run_with_clients(session, tokens: list[str]) -> int:
    file_repo = CsvFileRepository(session)
    params_repo = ParametersRepository(session)
    run_repo = RunRepository(session)
    client_repo = ClientRepository(session)

    file = file_repo.create(
        file_repo.model(name="f.csv", path_or_url="/tmp/f.csv")
    )
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
            multipliers={},
        )
    )
    run = run_repo.create(
        run_repo.model(
            algorithm="simplex",
            execution_time_ms=0,
            status="pending",
            parameters_id=params.id,
            csv_file_id=file.id,
        )
    )

    clients = [
        OptimizationClient(
            token=token,
            pd=0.1,
            payment_capacity=1000,
            propensity_score=0.5 if token == "t1" else 0.8,
        )
        for token in tokens
    ]
    client_repo.bulk_upsert_from_ingestion(clients, run.id)
    return run.id


def test_load_clients_for_job_uses_persisted_records(in_memory_db):
    with get_db_session() as session:
        run_id = _seed_run_with_clients(session, ["t1", "t2"])

    job = OptimizationJobSchema(
        run_id=run_id,
        algorithm="simplex",
        parameters_id=1,
        client_tokens=["t2", "t1"],
    )
    clients = load_clients_for_job(job)

    assert len(clients) == 2
    assert [client.token for client in clients] == ["t2", "t1"]
    assert clients[0].product_pd == pytest.approx(0.1)
    assert clients[0].payment_capacity == pytest.approx(1000.0)


def test_load_clients_for_job_empty_run_raises(in_memory_db):
    with get_db_session() as session:
        run_id = _seed_run_with_clients(session, ["t1"])

    job = OptimizationJobSchema(
        run_id=run_id,
        algorithm="simplex",
        parameters_id=1,
        client_tokens=["missing"],
    )

    with pytest.raises(ValueError, match="No persisted client"):
        load_clients_for_job(job)
