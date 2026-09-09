"""Execution-detail and PDF tests."""

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
from src.services.statistics_service import (
    build_run_result_csv,
    generate_report_pdf,
    get_execution_detail,
    get_execution_history,
)
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


def test_execution_history_includes_timing_fields(in_memory_db):
    run_id = seed_comparable_run(execution_time_ms=5000)

    data = get_execution_history(page=1, page_size=10)
    item = data["items"][0]

    assert item["run_id"] == run_id
    assert item["execution_time_ms"] == 5000
    assert item["approved"] == 1
    assert item["started_at"] is not None


def test_get_execution_detail_returns_log_and_distribution(in_memory_db):
    run_id = seed_comparable_run(execution_time_ms=1200)

    detail = get_execution_detail(run_id)

    assert detail["run_id"] == run_id
    assert detail["distribution"]["full"] >= 0
    assert len(detail["operational_log"]) >= 2
    assert detail["download_csv_url"] == f"/results/executions/{run_id}/download"
    assert detail["parameters"] is not None
    assert detail["limit_ranges"]


def test_execution_detail_endpoint_returns_200(in_memory_db):
    run_id = seed_comparable_run()

    client = TestClient(create_app())
    resp = client.get(f"/results/executions/{run_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["run_id"] == run_id
    assert body["data"]["operational_log"]


def test_generate_report_pdf_returns_bytes(in_memory_db):
    run_id = seed_comparable_run()

    pdf_bytes, filename = generate_report_pdf(run_id=run_id)

    assert filename == f"report-run-{run_id}.pdf"
    assert pdf_bytes.startswith(b"%PDF")


def test_report_pdf_endpoint_returns_pdf(in_memory_db):
    run_id = seed_comparable_run()

    client = TestClient(create_app())
    resp = client.get("/results/report/pdf", params={"run_id": run_id})

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


def test_build_run_result_csv_joins_optimized_limits(in_memory_db, monkeypatch):
    import io

    import pandas as pd

    run_id = seed_comparable_run()

    # The input file contains original columns plus token; one token was not processed by the run.
    df_input = pd.DataFrame(
        {
            "token": [f"run{run_id}_c1", f"run{run_id}_c2", "unprocessed"],
            "offered_limit": [1000, 2000, 3000],
            "score_interno": [700, 650, 720],
        }
    )
    input_bytes = df_input.to_csv(index=False).encode("utf-8")

    import src.utils.minio as minio

    monkeypatch.setattr(
        minio, "get_object_bytes", lambda path: (input_bytes, "text/csv")
    )

    content, filename = build_run_result_csv(run_id)
    out = pd.read_csv(io.BytesIO(content))

    assert filename == "result_clients.csv"
    # Original columns are preserved and the new algorithm column is present.
    assert {"token", "offered_limit", "score_interno", "suggested_limit"} <= set(
        out.columns
    )
    limits = dict(zip(out["token"], out["suggested_limit"]))
    assert limits[f"run{run_id}_c1"] == 2500.0
    assert limits[f"run{run_id}_c2"] == 0.0
    # A client outside the run receives no limit.
    assert pd.isna(limits["unprocessed"])
