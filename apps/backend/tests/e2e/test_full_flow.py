"""Tests E2E in-process: upload → queue mock → worker → status → result."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from helpers import sample_csv

from src.models.run import RunState
from src.repositories import ClientRepository, RunRepository
from src.utils.db.session import get_db_session
from src.workers.optimization_worker import handle_optimization_message


def test_parameters_active_exists(e2e_client):
    client, _ = e2e_client
    resp = client.get("/parameters/active")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["data"]["id"] is not None


def test_upload_returns_run_id_and_queues_job(e2e_client):
    client, queue = e2e_client
    csv = sample_csv("t1", "t2")

    resp = client.post(
        "/ingestion/upload",
        files={"file": ("clients.csv", csv, "text/csv")},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "ok"
    assert body["data"]["state"] == "queued"
    run_id = body["data"]["run_id"]

    status = client.get(f"/optimization/runs/{run_id}").json()
    assert status["state"] == RunState.WAITING_FOR_PROCESSING.value

    assert len(queue.published_messages) == 1
    job = queue.published_messages[0]["payload"]
    assert job["run_id"] == run_id
    assert job["client_tokens"] == ["t1", "t2"]

    with get_db_session() as session:
        clients = ClientRepository(session).get_by_run(run_id)
        assert {c.token for c in clients} == {"t1", "t2"}


def test_result_not_available_before_worker_finishes(e2e_client):
    client, _ = e2e_client
    csv = sample_csv("t1")

    resp = client.post(
        "/ingestion/upload",
        files={"file": ("one.csv", csv, "text/csv")},
    )
    run_id = resp.json()["data"]["run_id"]

    assert client.get(f"/optimization/runs/{run_id}/result").status_code == 404


def test_full_flow_upload_worker_result_simplex_ortools(e2e_client):
    client, queue = e2e_client
    csv = sample_csv("o1", "o2")

    resp = client.post(
        "/ingestion/upload",
        files={"file": ("batch_ortools.csv", csv, "text/csv")},
        data={"algorithm": "simplex_ortools"},
    )
    assert resp.status_code == 202
    assert resp.json()["data"]["algorithm"] == "simplex_ortools"

    run_id = resp.json()["data"]["run_id"]
    job = queue.published_messages[-1]["payload"]
    assert job["algorithm"] == "simplex_ortools"

    asyncio.run(handle_optimization_message(job))

    status = client.get(f"/optimization/runs/{run_id}").json()
    assert status["state"] == RunState.COMPLETED.value
    assert status["error"] is None

    result = client.get(f"/optimization/runs/{run_id}/result").json()
    assert result["final_status"] == "success"
    assert result["algorithm"] == "simplex_ortools"

    with get_db_session() as session:
        run = RunRepository(session).get_by_id(run_id)
        assert run.algorithm == "simplex_ortools"
        assert run.status == "success"
        assert run.result is not None


def test_full_flow_upload_worker_result(e2e_client):
    client, queue = e2e_client
    csv = sample_csv("c1", "c2")

    resp = client.post(
        "/ingestion/upload",
        files={"file": ("batch.csv", csv, "text/csv")},
    )
    run_id = resp.json()["data"]["run_id"]
    job = queue.published_messages[0]["payload"]

    asyncio.run(handle_optimization_message(job))

    status = client.get(f"/optimization/runs/{run_id}").json()
    assert status["state"] == RunState.COMPLETED.value
    assert status["error"] is None
    assert status["finished_at"] is not None

    result_resp = client.get(f"/optimization/runs/{run_id}/result")
    assert result_resp.status_code == 200
    result = result_resp.json()
    assert result["final_status"] == "success"
    assert result["result_id"] is not None

    with get_db_session() as session:
        run = RunRepository(session).get_by_id(run_id)
        assert run.status == "success"
        assert run.result is not None
        assert run.execution_time_ms > 0

        from src.repositories import RunClusterRepository

        clusters = RunClusterRepository(session).get_by_run(run_id)
        assert len(clusters) >= 1


def test_status_evolves_from_queued_to_completed(e2e_client):
    client, queue = e2e_client
    csv = sample_csv("ev1")

    resp = client.post(
        "/ingestion/upload",
        files={"file": ("evolve.csv", csv, "text/csv")},
    )
    run_id = resp.json()["data"]["run_id"]

    before = client.get(f"/optimization/runs/{run_id}").json()
    assert before["state"] == RunState.WAITING_FOR_PROCESSING.value

    asyncio.run(handle_optimization_message(queue.published_messages[0]["payload"]))

    after = client.get(f"/optimization/runs/{run_id}").json()
    assert after["state"] == RunState.COMPLETED.value


def test_two_uploads_processed_in_fifo_order(e2e_client):
    client, queue = e2e_client
    run_ids: list[int] = []

    for name, token in (("first.csv", "f1"), ("second.csv", "s1")):
        resp = client.post(
            "/ingestion/upload",
            files={"file": (name, sample_csv(token), "text/csv")},
        )
        run_ids.append(resp.json()["data"]["run_id"])

    assert len(queue.published_messages) == 2
    processed_order: list[int] = []

    async def process_all() -> None:
        for message in queue.published_messages:
            payload = message["payload"]
            processed_order.append(payload["run_id"])
            await handle_optimization_message(payload)

    asyncio.run(process_all())

    assert processed_order == run_ids

    for run_id in run_ids:
        status = client.get(f"/optimization/runs/{run_id}").json()
        assert status["state"] == RunState.COMPLETED.value
        assert client.get(f"/optimization/runs/{run_id}/result").status_code == 200
