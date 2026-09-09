import asyncio
import os
import sys

import pytest

# Ensure project importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.utils.db.session as db_session
from src.schema.database.base import Base
from src.schema.database.run import Run
from src.repositories import CsvFileRepository, ParametersRepository, RunRepository
from src.services.async_service import AsyncQueueConfig, AsyncQueueService
from src.services.optimization_service import enqueue_run_for_processing
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


@pytest.fixture()
def queue_service(monkeypatch):
    monkeypatch.setenv("ASYNC_QUEUE_USE_MOCK", "true")
    service = AsyncQueueService(AsyncQueueConfig(use_mock=True))
    monkeypatch.setattr(
        "src.services.optimization_service.DEFAULT_ASYNC_QUEUE_SERVICE",
        service,
    )
    return service


def _seed_run(session) -> tuple[int, int]:
    file_repo = CsvFileRepository(session)
    parameters_repo = ParametersRepository(session)
    run_repo = RunRepository(session)

    file = file_repo.create(file_repo.model(name="f.csv", path_or_url="/tmp/f.csv"))
    Param = parameters_repo.model
    params = parameters_repo.create(
        Param(
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
        Run(
            algorithm="simplex",
            execution_time_ms=0,
            status="pending",
            parameters_id=params.id,
            csv_file_id=file.id,
        )
    )
    return run.id, params.id


def test_enqueue_run_for_processing_adds_job_to_queue(in_memory_db, queue_service):
    with get_db_session() as session:
        run_id, params_id = _seed_run(session)

    result = asyncio.run(
        enqueue_run_for_processing(run_id, "simplex", parameters_id=params_id)
    )

    assert result["run_id"] == run_id
    assert result["job"]["run_id"] == run_id
    assert result["queue"]
    assert queue_service.snapshot()["pending_messages"] == 1


def test_queue_processes_multiple_runs_in_order(in_memory_db, queue_service):
    with get_db_session() as session:
        run_id_1, params_id = _seed_run(session)
        run_id_2, _ = _seed_run(session)

    for run_id in (run_id_1, run_id_2):
        asyncio.run(
            enqueue_run_for_processing(run_id, "simplex", parameters_id=params_id)
        )

    processed: list[int] = []

    async def fake_handler(payload: dict) -> None:
        processed.append(payload["run_id"])

    processed_count = asyncio.run(
        queue_service.consume_optimization_jobs(fake_handler, max_messages=2)
    )

    assert processed_count == 2
    assert processed == [run_id_1, run_id_2]
