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


def test_client_repository_bulk_upsert_from_ingestion(in_memory_db):
    from decimal import Decimal

    from src.repositories import ClientRepository
    from src.models.client import OptimizationClient

    with get_db_session() as s:
        client_repo = ClientRepository(s)
        client_repo.bulk_upsert_from_ingestion(
            [
                OptimizationClient(
                    token="t1",
                    pd=Decimal("0.2"),
                    payment_capacity=Decimal("1500"),
                    propensity_score=Decimal("0.7"),
                )
            ],
            run_id=1,
        )
        saved = client_repo.get_by_run(1)
        assert len(saved) == 1
        assert saved[0].token == "t1"
        assert float(saved[0].last_suggested_limit) == 0.0


def test_client_repository_upsert_behaviour(in_memory_db):
    from src.repositories import ClientRepository

    with get_db_session() as s:
        client_repo = ClientRepository(s)
        Client = client_repo.model
        c = client_repo.create(
            Client(
                token="t1",
                last_run_id=1,
                last_suggested_limit=100,
                payment_capacity=1000,
                score=0.5,
                pd=0.1,
            )
        )
        assert c.id is not None

        client_repo.upsert_client(
            token="t1",
            run_id=2,
            suggested_limit=200,
            payment_capacity=1200,
            score=0.6,
            pd=0.05,
        )
        updated = client_repo.get_by_token("t1")
        assert updated.last_run_id == 2
        assert float(updated.last_suggested_limit) == 200.0


def test_run_repository_mark_success_and_mark_error(in_memory_db):
    from src.repositories import RunRepository, CsvFileRepository, ParametersRepository

    with get_db_session() as s:
        run_repo = RunRepository(s)
        File = CsvFileRepository(s).model
        Run = run_repo.model
        file = File(name="f", path_or_url="p")
        s.add(file)
        s.commit()

        params_repo = ParametersRepository(s)
        Param = params_repo.model
        params = params_repo.create(
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

        run = Run(
            algorithm="simplex",
            execution_time_ms=0,
            status="error",
            parameters_id=params.id,
            csv_file_id=file.id,
        )
        created = run_repo.create(run)
        rid = created.id

        run_repo.mark_success(rid, 123)
        r = run_repo.get_by_id(rid)
        assert r.status == "success"
        assert r.execution_time_ms == 123

        run_repo.mark_error(rid, 50)
        r2 = run_repo.get_by_id(rid)
        assert r2.status == "error"
