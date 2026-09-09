import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.utils.db.session as db_session
from src.models.run import RunState, ETAPA_LABELS, RunStatus
from src.repositories import CsvFileRepository, ParametersRepository, RunRepository
from src.schema.database.base import Base
from src.services.optimization_service import get_status, update_run_progress
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


def _seed_run(session, *, status: str = RunStatus.PENDING.value) -> tuple[int, int]:
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
            status=status,
            parameters_id=params.id,
            csv_file_id=file.id,
        )
    )
    return run.id, params.id


def test_update_run_progress_persists_state(in_memory_db):
    with get_db_session() as session:
        run_id, _ = _seed_run(session)

    for state in (
        RunState.INGESTION,
        RunState.CALCULATING_CONSTRAINTS,
        RunState.TABLEAU_CALCULATION,
        RunState.GENERATING_RECOMMENDATIONS,
        RunState.VALIDATING_CONSTRAINTS,
        RunState.COMPLETED,
    ):
        update_run_progress(
            run_id,
            state,
            start=True,
            finish=state == RunState.COMPLETED,
        )

    status = get_status(run_id)
    assert status is not None
    assert status["state"] == RunState.COMPLETED.value
    assert status["current_stage"] == ETAPA_LABELS[RunState.COMPLETED]
    assert status["started_at"] is not None
    assert status["finished_at"] is not None


def test_estados_operacionais_persistidos(in_memory_db):
    with get_db_session() as session:
        run_id, _ = _seed_run(session)

    update_run_progress(run_id, RunState.GENERATING_RECOMMENDATIONS, start=True)

    with get_db_session() as session:
        run = RunRepository(session).get_by_id(run_id)
        assert run.state_operacional == "generating_recommendations"

    status = get_status(run_id)
    assert status["current_stage"] == ETAPA_LABELS[RunState.GENERATING_RECOMMENDATIONS]
