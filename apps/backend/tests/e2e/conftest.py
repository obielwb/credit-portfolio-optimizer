

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.utils.db.session as db_session
from src.schema.database.base import Base
from src.schema.database.parameters import Parameters
from src.repositories import ParametersRepository
from src.services.async_service import AsyncQueueConfig, AsyncQueueService
from src.utils.db.bootstrap import default_parameters_values
from src.utils.db.session import get_db_session

BACKEND_ROOT = Path(__file__).resolve().parents[2]
OPTIMIZER_ROOT = BACKEND_ROOT.parent / "optimizer"

sys.path.insert(0, str(BACKEND_ROOT))


def _e2e_integration_enabled() -> bool:
    return os.getenv("RUN_E2E_INTEGRATION", "").lower() in {"1", "true", "yes"}


@pytest.fixture()
def sqlite_e2e_db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    db_session.SessionLocal = SessionLocal
    yield engine


@pytest.fixture()
def seed_parameters(sqlite_e2e_db):
    values = default_parameters_values()
    with get_db_session() as session:
        repo = ParametersRepository(session)
        if repo.get_latest() is None:
            repo.create(
                Parameters(
                    utilization_rate=values["utilization_rate"],
                    lgd=values["lgd"],
                    min_pd=values["min_pd"],
                    max_pd=values["max_pd"],
                    filter=values["filter"],
                    max_limit=values["max_limit"],
                    baseline_default_rate=values[
                        "baseline_default_rate"
                    ],
                    min_limit=values["min_limit"],
                    discretize=values["discretize"],
                    interchange=values["interchange"],
                    max_rejected_limit=values["max_rejected_limit"],
                    enabled=values["enabled"],
                    n_clusters=values["n_clusters"],
                    max_clients_per_cluster=values["max_clients_per_cluster"],
                    min_clusters=values["min_clusters"],
                    multipliers=values["multipliers"],
                )
            )


@pytest.fixture()
def e2e_client(seed_parameters, monkeypatch):


    monkeypatch.setenv("ASYNC_QUEUE_USE_MOCK", "true")
    monkeypatch.setenv("ALGORITHM_ROOT", str(OPTIMIZER_ROOT))

    queue_service = AsyncQueueService(AsyncQueueConfig(use_mock=True))
    monkeypatch.setattr(
        "src.services.optimization_service.DEFAULT_ASYNC_QUEUE_SERVICE",
        queue_service,
    )

    import src.services.ingestion_service as ingestion_service

    monkeypatch.setattr(
        ingestion_service,
        "upload_csv_to_minio",
        lambda contents, filename, file_ref=None: f"minio://test/{filename}",
    )

    from src.main import create_app

    client = TestClient(create_app())
    return client, queue_service


@pytest.fixture()
def e2e_integration_enabled():
    return _e2e_integration_enabled()
