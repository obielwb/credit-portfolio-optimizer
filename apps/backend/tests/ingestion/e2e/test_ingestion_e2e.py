import os
import sys

import pytest

# Ensure project importable
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.utils.db.session as db_session
from src.schema.database.base import Base
from src.main import create_app
from src.services.async_service import AsyncQueueConfig, AsyncQueueService


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


def test_ingestion_controller_creates_run_and_enqueues(in_memory_db, monkeypatch):
    app = create_app()
    from src.controllers.ingestion_controller import router as ingestion_router
    import src.services.ingestion_service as ingestion_service
    from src.repositories import ParametersRepository, RunRepository
    from src.utils.db.session import get_db_session

    monkeypatch.setenv("ASYNC_QUEUE_USE_MOCK", "true")
    queue_service = AsyncQueueService(AsyncQueueConfig(use_mock=True))
    monkeypatch.setattr(
        "src.services.optimization_service.DEFAULT_ASYNC_QUEUE_SERVICE",
        queue_service,
    )

    with get_db_session() as session:
        parameters_repo = ParametersRepository(session)
        Param = parameters_repo.model
        parameters_repo.create(
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

    app.include_router(ingestion_router)
    monkeypatch.setattr(
        ingestion_service,
        "upload_csv_to_minio",
        lambda contents, filename, file_ref=None: f"minio://test/{filename}",
    )
    client = TestClient(app)

    csv = (
        "token,default_probability,payment_capacity,contract_propensity,filter_flag\n"
        "t1,0.1,1000,0.5,0\n"
    )

    files = {"file": ("test.csv", csv, "text/csv")}
    resp = client.post("/ingestion/upload", files=files)
    assert resp.status_code == 202
    json = resp.json()
    assert json["status"] == "ok"
    assert "data" in json
    assert json["meta"]["queue"]
    run_id = json["data"]["run_id"]

    with get_db_session() as session:
        run_repo = RunRepository(session)
        run = run_repo.get_by_id(run_id)
        assert run is not None
        assert run.csv_file_id is not None
        assert run.status == "pending"

    from src.repositories import CsvFileRepository

    with get_db_session() as session:
        file_repo = CsvFileRepository(session)
        file = file_repo.get_by_id(run.csv_file_id)
        assert file is not None
        assert file.path_or_url.startswith("minio://test/")
        assert file.name == "test.csv"

    assert len(queue_service.published_messages) == 1
    job_payload = queue_service.published_messages[0]["payload"]
    assert job_payload["run_id"] == run_id
    assert job_payload["client_tokens"] == ["t1"]

    from src.repositories import ClientRepository

    with get_db_session() as session:
        client_repo = ClientRepository(session)
        clients = client_repo.get_by_run(run_id)
        assert len(clients) == 1
        assert clients[0].token == "t1"
        assert float(clients[0].pd) == pytest.approx(0.1)
        assert float(clients[0].payment_capacity) == pytest.approx(1000.0)
        assert float(clients[0].score) == pytest.approx(0.5)
        assert float(clients[0].last_suggested_limit) == pytest.approx(0.0)


def test_ingestion_invalid_extension_returns_400(in_memory_db):
    app = create_app()
    from src.controllers.ingestion_controller import router as ingestion_router

    app.include_router(ingestion_router)
    client = TestClient(app)

    files = {"file": ("test.txt", "notcsv", "text/plain")}
    resp = client.post("/ingestion/upload", files=files)
    assert resp.status_code == 400
    j = resp.json()
    assert j["status"] == "error"
    assert j["code"] == "INVALID_FILE_EXTENSION"


def test_ingestion_empty_file_returns_400(in_memory_db):
    app = create_app()
    from src.controllers.ingestion_controller import router as ingestion_router

    app.include_router(ingestion_router)
    client = TestClient(app)

    files = {"file": ("empty.csv", b"", "text/csv")}
    resp = client.post("/ingestion/upload", files=files)
    assert resp.status_code == 400
    j = resp.json()
    assert j["code"] == "EMPTY_FILE"
