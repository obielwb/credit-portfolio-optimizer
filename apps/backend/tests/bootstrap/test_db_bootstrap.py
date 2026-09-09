import os
import sys

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import src.utils.db.session as db_session
from src.repositories import ParametersRepository
from src.utils.db.bootstrap import (
    bootstrap_database,
    create_schema,
    import_all_models,
    seed_default_parameters,
)
from src.utils.db.session import get_db_session


@pytest.fixture()
def sqlite_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine
    engine.dispose()


def test_import_all_models_registers_expected_tables(sqlite_engine):
    import_all_models()
    from src.schema.database.base import Base

    create_schema(sqlite_engine)

    tables = set(inspect(sqlite_engine).get_table_names())
    assert {
        "parameters",
        "run",
        "files_csv",
        "results",
        "clients",
        "audit_clients",
        "run_clusters",
    }.issubset(tables)

    results_columns = {
        column["name"] for column in inspect(sqlite_engine).get_columns("results")
    }
    assert {"approved", "approval_rate"}.issubset(results_columns)


def test_seed_default_parameters_is_idempotent(sqlite_engine):
    create_schema(sqlite_engine)
    SessionLocal = sessionmaker(bind=sqlite_engine, expire_on_commit=False)

    with SessionLocal() as session:
        first_id = seed_default_parameters(session)
        session.commit()
        second_id = seed_default_parameters(session)
        session.commit()

    assert first_id is not None
    assert second_id is None


def test_bootstrap_database_configures_session_and_seed(sqlite_engine):
    engine, seeded_id = bootstrap_database(
        sqlite_engine,
        seed=True,
        configure_session=True,
    )

    assert engine is sqlite_engine
    assert seeded_id is not None

    with get_db_session() as session:
        params_repo = ParametersRepository(session)
        latest = params_repo.get_latest()
        assert latest is not None
        assert latest.id == seeded_id
        assert float(latest.utilization_rate) == pytest.approx(0.7)
        assert float(latest.lgd) == pytest.approx(0.8)
        assert latest.min_clusters == 100

    _, seeded_again = bootstrap_database(
        sqlite_engine,
        seed=True,
        configure_session=False,
    )
    assert seeded_again is None
