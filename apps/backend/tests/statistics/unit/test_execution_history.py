"""Enriched run-history tests."""

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
from src.schema.database.base import Base
from src.services.statistics_service import get_execution_history
from tests.comparison.conftest import seed_comparable_run


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


def test_get_execution_history_includes_kpis_for_success_runs(in_memory_db):
    seed_comparable_run(total_limit=5000.0, total_return=200.0)

    data = get_execution_history(page=1, page_size=10)

    assert data["total_items"] == 1
    item = data["items"][0]
    assert item["total_limit"] == 5000.0
    assert item["total_return"] == 200.0
    assert item["approval_rate"] == 0.5


def test_get_execution_history_filters_by_status(in_memory_db):
    seed_comparable_run(status="success")
    seed_comparable_run(status="error", file_name="error.csv")

    data = get_execution_history(page=1, page_size=10, status="success")

    assert data["total_items"] == 1
    assert data["items"][0]["status"] == "success"


def test_executions_history_endpoint_supports_status_query(in_memory_db):
    seed_comparable_run(status="success")
    seed_comparable_run(status="error", file_name="error.csv")

    client = TestClient(create_app())
    resp = client.get("/results/executions/history", params={"status": "success"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["total_items"] == 1
    assert body["data"]["items"][0]["total_limit"] == 5000.0
