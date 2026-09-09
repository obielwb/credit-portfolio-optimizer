import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.utils.db.session as db_session
from src.repositories import (
    CsvFileRepository,
    ClientRepository,
    ClientHistoryRepository,
    ParametersRepository,
    ResultRepository,
    RunRepository,
)
from src.models.client import OptimizationClient
from src.models.run import RunStatus
from src.schema.database.base import Base
from src.services.optimization_service import (
    complete_run,
    enqueue_run_for_processing,
    fail_run,
    get_status,
)
from src.custom_types import ClientChangeType
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


def test_fail_run_persists_error_reason(in_memory_db):
    with get_db_session() as session:
        run_id, _ = _seed_run(session)

    fail_run(run_id, "failure while loading clients", stage="worker")

    status = get_status(run_id)
    assert status is not None
    assert status["error"] == "[worker] failure while loading clients"
    assert status["state"] == "failed"

    with get_db_session() as session:
        run = RunRepository(session).get_by_id(run_id)
        assert run.status == RunStatus.ERROR.value
        assert run.error_reason == "[worker] failure while loading clients"


def test_fail_run_does_not_overwrite_successful_run(in_memory_db):
    with get_db_session() as session:
        run_id, _ = _seed_run(session, status=RunStatus.SUCCESS.value)

    fail_run(run_id, "failure tardia", stage="worker")

    with get_db_session() as session:
        run = RunRepository(session).get_by_id(run_id)
        assert run.status == RunStatus.SUCCESS.value
        assert run.error_reason is None


def test_enqueue_failure_persists_error_reason(in_memory_db, monkeypatch):
    with get_db_session() as session:
        run_id, params_id = _seed_run(session)

    async def boom(*_args, **_kwargs):
        raise RuntimeError("queue unavailable")

    monkeypatch.setattr(
        "src.services.optimization_service.DEFAULT_ASYNC_QUEUE_SERVICE.publish_optimization_job",
        boom,
    )

    with pytest.raises(RuntimeError, match="queue unavailable"):
        asyncio.run(
            enqueue_run_for_processing(run_id, "simplex", parameters_id=params_id)
        )

    status = get_status(run_id)
    assert status is not None
    assert status["error"] == "[queueing] queue unavailable"


def test_get_status_pending_run(in_memory_db):
    with get_db_session() as session:
        run_id, _ = _seed_run(session, status=RunStatus.PENDING.value)

    status = get_status(run_id)
    assert status is not None
    assert status["error"] is None
    assert status["state"] == "waiting_for_processing"
    assert status["current_stage"] == "Waiting processamento"


def test_complete_run_registers_history_with_change_type(in_memory_db):
    with get_db_session() as session:
        run_id, _ = _seed_run(session)
        ClientRepository(session).bulk_upsert_from_ingestion(
            [
                OptimizationClient(
                    token="t1",
                    pd=0.1,
                    payment_capacity=1000,
                    propensity_score=0.5,
                )
            ],
            run_id,
        )

    complete_run(
        run_id,
        {
            "client_count": 1,
            "result_portfolio": {
                "total_clients": 1,
                "total_limit": 500.0,
                "total_income": 10.0,
                "total_loss": 1.0,
                "total_return": 9.0,
                "financial_default_rate": 0.05,
                "baseline_default_rate": 0.05,
                "clients": [
                    {
                        "client": {
                            "token": "t1",
                            "product_pd": 0.1,
                            "payment_capacity": 1000.0,
                            "contract_propensity_score": 0.5,
                        },
                        "suggested_limit": 500.0,
                    }
                ],
            },
        },
    )

    with get_db_session() as session:
        run = RunRepository(session).get_by_id(run_id)
        assert run.status == RunStatus.SUCCESS.value
        assert run.error_reason is None
        assert ResultRepository(session).find_by(run_id=run_id)

        history = ClientHistoryRepository(session).get_by_token("t1")
        assert len(history) == 1
        assert history[0].change_type == ClientChangeType.LIMIT_UPDATED
        assert history[0].run_id == run_id
        assert history[0].previous_state == {
            "run_id": run_id,
            "suggested_limit": 0.0,
        }
        assert history[0].current_state == {
            "run_id": run_id,
            "suggested_limit": 500.0,
            "payment_capacity": 1000.0,
            "score": 0.5,
            "pd": 0.1,
        }

        client = ClientRepository(session).get_by_token("t1")
        assert float(client.last_suggested_limit) == 500.0


def test_complete_run_inserts_new_client_and_audit(in_memory_db):

    with get_db_session() as session:
        run_id, _ = _seed_run(session)

    complete_run(
        run_id,
        {
            "client_count": 1,
            "result_portfolio": {
                "total_clients": 1,
                "total_limit": 700.0,
                "clients": [
                    {
                        "client": {
                            "token": "new1",
                            "product_pd": 0.2,
                            "payment_capacity": 2000.0,
                            "contract_propensity_score": 0.6,
                        },
                        "suggested_limit": 700.0,
                    }
                ],
            },
        },
    )

    with get_db_session() as session:
        client = ClientRepository(session).get_by_token("new1")
        assert client is not None
        assert client.last_run_id == run_id
        assert float(client.last_suggested_limit) == 700.0

        history = ClientHistoryRepository(session).get_by_token("new1")
        assert len(history) == 1
        assert history[0].change_type == ClientChangeType.NEW_CLIENT
        assert history[0].previous_state is None
        assert history[0].current_state == {
            "run_id": run_id,
            "suggested_limit": 700.0,
            "payment_capacity": 2000.0,
            "score": 0.6,
            "pd": 0.2,
        }


def test_complete_run_persists_run_clusters(in_memory_db):
    with get_db_session() as session:
        run_id, _ = _seed_run(session)

    complete_run(
        run_id,
        {
            "client_count": 2,
            "clusters": [
                {
                    "cluster_id": 1,
                    "total_clients": 10,
                    "average_pd": 0.12,
                    "average_score": 0.45,
                    "average_capacity": 5000.0,
                    "policy_name": "balanced",
                    "leverage_multiplier": 1.0,
                },
                {
                    "cluster_id": 2,
                    "total_clients": 5,
                    "average_pd": 0.20,
                    "average_score": 0.30,
                    "average_capacity": 4200.0,
                    "policy_name": "restrictive",
                    "leverage_multiplier": 0.75,
                },
            ],
            "result_portfolio": {
                "total_limit": 1000.0,
                "clients": [],
            },
        },
    )

    with get_db_session() as session:
        from src.repositories import RunClusterRepository

        clusters = RunClusterRepository(session).get_by_run(run_id)
        assert len(clusters) == 2
        assert {cluster.cluster_id for cluster in clusters} == {1, 2}
        assert clusters[0].policy_name in {"balanced", "restrictive"}
