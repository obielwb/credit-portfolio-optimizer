

from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import src.utils.db.session as db_session
from src.main import create_app
from src.repositories import ParametersRepository, RunRepository
from src.schema.database.base import Base
from src.services.async_service import AsyncQueueConfig, AsyncQueueService
from src.utils.db.session import get_db_session


@pytest.fixture()
def upload_client(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    db_session.SessionLocal = SessionLocal

    monkeypatch.setenv("ASYNC_QUEUE_USE_MOCK", "true")
    queue_service = AsyncQueueService(AsyncQueueConfig(use_mock=True))
    monkeypatch.setattr(
        "src.services.optimization_service.DEFAULT_ASYNC_QUEUE_SERVICE",
        queue_service,
    )
    monkeypatch.setattr(
        "src.services.ingestion_service.upload_csv_to_minio",
        lambda contents, filename, file_ref=None: f"minio://test/{filename}",
    )

    with get_db_session() as session:
        params_repo = ParametersRepository(session)
        Param = params_repo.model
        params_repo.create(
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
                enabled=False,
                n_clusters=None,
                max_clients_per_cluster=100,
                min_clusters=100,
                multipliers={},
            )
        )

    client = TestClient(create_app())
    csv = (
        "token,default_probability,payment_capacity,contract_propensity,filter_flag\n"
        "t1,0.1,1000,0.5,0\n"
    )
    yield client, csv, queue_service


def test_upload_accepts_branch_bound_alias(upload_client):
    client, csv, queue = upload_client

    resp = client.post(
        "/ingestion/upload",
        files={"file": ("batch.csv", csv, "text/csv")},
        data={"algorithm": "Branch and Bound"},
    )

    assert resp.status_code == 202
    body = resp.json()
    assert body["data"]["algorithm"] == "branch_bound"

    run_id = body["data"]["run_id"]
    with get_db_session() as session:
        run = RunRepository(session).get_by_id(run_id)
        assert run.algorithm == "branch_bound"

    job = queue.published_messages[0]["payload"]
    assert job["algorithm"] == "branch_bound"


def test_upload_accepts_simplex_ortools(upload_client):
    client, csv, queue = upload_client

    resp = client.post(
        "/ingestion/upload",
        files={"file": ("batch.csv", csv, "text/csv")},
        data={"algorithm": "Simplex OR-Tools"},
    )

    assert resp.status_code == 202
    body = resp.json()
    assert body["data"]["algorithm"] == "simplex_ortools"

    run_id = body["data"]["run_id"]
    with get_db_session() as session:
        run = RunRepository(session).get_by_id(run_id)
        assert run.algorithm == "simplex_ortools"

    job = queue.published_messages[-1]["payload"]
    assert job["algorithm"] == "simplex_ortools"


def test_upload_rejects_invalid_algorithm(upload_client):
    client, csv, _queue = upload_client

    resp = client.post(
        "/ingestion/upload",
        files={"file": ("batch.csv", csv, "text/csv")},
        data={"algorithm": "genetic"},
    )

    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_ALGORITHM"
