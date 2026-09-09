import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.utils.db.session as db_session
from src.repositories import CsvFileRepository, ParametersRepository, RunRepository
from src.schema.database.base import Base
from src.services.optimization_service import get_status
from src.utils.db.session import get_db_session
from src.workers.optimization_worker import handle_optimization_message


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


def test_worker_invalid_payload_records_fail_run(in_memory_db):
    with get_db_session() as session:
        file_repo = CsvFileRepository(session)
        params_repo = ParametersRepository(session)
        run_repo = RunRepository(session)
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
        run_id = run.id
        params_id = params.id

    payload = {"run_id": run_id, "algorithm": "invalido", "parameters_id": params_id}

    with pytest.raises(Exception):
        asyncio.run(handle_optimization_message(payload))

    status = get_status(run_id)
    assert status is not None
    assert status["state"] == "failed"
    assert status["error"].startswith("[worker]")
