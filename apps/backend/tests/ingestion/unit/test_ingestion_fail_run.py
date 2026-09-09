import asyncio
import io
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.utils.db.session as db_session
from src.repositories import ParametersRepository, RunRepository
from src.schema.database.base import Base
from src.services import ingestion_service
from src.services.optimization_service import get_status
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


def _seed_parameters(session) -> None:
    params_repo = ParametersRepository(session)
    params_repo.create(
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


def test_ingestion_client_persist_failure_records_fail_run(in_memory_db, monkeypatch):
    with get_db_session() as session:
        _seed_parameters(session)

    monkeypatch.setattr(
        ingestion_service,
        "upload_csv_to_minio",
        lambda contents, filename, file_ref=None: f"minio://test/{filename}",
    )

    def boom(self, _clients, _run_id):
        raise RuntimeError("failure while persisting clients")

    monkeypatch.setattr(
        "src.services.ingestion_service.ClientRepository.bulk_upsert_from_ingestion",
        boom,
    )

    csv = (
        "token,default_probability,payment_capacity,contract_propensity,filter_flag\n"
        "t1,0.1,1000,0.5,0\n"
    )

    with pytest.raises(RuntimeError, match="failure while persisting clients"):
        asyncio.run(ingestion_service.start_ingestion(csv.encode(), "test.csv"))

    with get_db_session() as session:
        run = RunRepository(session).get_all()[-1]

    status = get_status(run.id)
    assert status is not None
    assert status["error"] == "[ingestion] failure while persisting clients"
    assert status["state"] == "failed"
