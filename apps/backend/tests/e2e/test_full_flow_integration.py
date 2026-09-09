

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from helpers import sample_csv

from src.models.run import RunState
from src.services.async_service import AsyncQueueConfig, AsyncQueueService
from src.utils.db.bootstrap import bootstrap_database
from src.workers.optimization_worker import handle_optimization_message

from conftest import OPTIMIZER_ROOT, _e2e_integration_enabled


@pytest.mark.skipif(
    not _e2e_integration_enabled(),
    reason="Local-infrastructure E2E test disabled (RUN_E2E_INTEGRATION=1)",
)
def test_e2e_rabbitmq_shared_queue(monkeypatch):
    """Publish through the API and consume through the same real RabbitMQ queue as the worker."""

    monkeypatch.setenv("POSTGRES_HOST", os.getenv("POSTGRES_HOST", "localhost"))
    monkeypatch.setenv("RABBITMQ_HOST", os.getenv("RABBITMQ_HOST", "localhost"))
    monkeypatch.setenv("MINIO_ENDPOINT", os.getenv("MINIO_ENDPOINT", "localhost:9000"))
    monkeypatch.setenv("ALGORITHM_ROOT", str(OPTIMIZER_ROOT))
    monkeypatch.setenv("ASYNC_QUEUE_USE_MOCK", "false")

    queue_name = f"optimization-e2e-{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("RABBITMQ_QUEUE_OPTIMIZATION", queue_name)

    bootstrap_database(seed=True, configure_session=True)

    publisher = AsyncQueueService(AsyncQueueConfig(use_mock=False))
    consumer = AsyncQueueService(AsyncQueueConfig(use_mock=False))
    monkeypatch.setattr(
        "src.services.optimization_service.DEFAULT_ASYNC_QUEUE_SERVICE",
        publisher,
    )

    import src.services.ingestion_service as ingestion_service

    monkeypatch.setattr(
        ingestion_service,
        "upload_csv_to_minio",
        lambda contents, filename, file_ref=None: f"minio://test/{filename}",
    )

    from src.main import create_app

    client = TestClient(create_app())
    csv = sample_csv("rq1", "rq2")
    resp = client.post(
        "/ingestion/upload",
        files={"file": ("rabbit.csv", csv, "text/csv")},
    )
    assert resp.status_code == 202
    run_id = resp.json()["data"]["run_id"]

    received: list[dict] = []

    async def capture_and_process(payload: dict) -> None:
        received.append(payload)
        await handle_optimization_message(payload)

    processed = asyncio.run(
        consumer.consume_optimization_jobs(capture_and_process, max_messages=1)
    )
    assert processed == 1
    assert received[0]["run_id"] == run_id

    status = client.get(f"/optimization/runs/{run_id}").json()
    assert status["state"] == RunState.COMPLETED.value
    assert client.get(f"/optimization/runs/{run_id}/result").status_code == 200
