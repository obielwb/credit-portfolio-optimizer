"""Tests E2E do comparison_controller."""

from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.main import create_app

from tests.comparison.conftest import seed_comparable_run


@pytest.fixture()
def client(comparison_db):
    return TestClient(create_app())


def test_get_run_snapshot_endpoint_returns_200(client):
    run_id = seed_comparable_run()

    resp = client.get(f"/comparison/runs/{run_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["data"]["run_id"] == run_id
    assert body["data"]["metrics"]["total_limit"] == 5000.0


def test_get_run_snapshot_endpoint_returns_404(client):
    resp = client.get("/comparison/runs/999")

    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "RUN_NOT_FOUND"


def test_compare_runs_endpoint_returns_200(client):
    ref_id = seed_comparable_run(total_limit=5000.0, total_return=200.0)
    cmp_id = seed_comparable_run(
        total_limit=6000.0,
        total_return=300.0,
        file_name="clients_b.csv",
    )

    resp = client.get(
        "/comparison/runs",
        params={"reference_run_id": ref_id, "compared_run_id": cmp_id},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["data"]["reference"]["run_id"] == ref_id
    assert body["data"]["compared"]["run_id"] == cmp_id
    assert body["data"]["deltas"]["total_limit"]["absoluto"] == 1000.0


def test_compare_runs_endpoint_returns_400_for_same_run(client):
    run_id = seed_comparable_run()

    resp = client.get(
        "/comparison/runs",
        params={"reference_run_id": run_id, "compared_run_id": run_id},
    )

    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "SAME_RUN_COMPARISON"


def test_compare_runs_endpoint_returns_404_for_missing_run(client):
    run_id = seed_comparable_run()

    resp = client.get(
        "/comparison/runs",
        params={"reference_run_id": run_id, "compared_run_id": 999},
    )

    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "RUN_NOT_FOUND"


def test_compare_runs_endpoint_returns_409_for_non_success_run(client):
    ref_id = seed_comparable_run()
    cmp_id = seed_comparable_run(status="error")

    resp = client.get(
        "/comparison/runs",
        params={"reference_run_id": ref_id, "compared_run_id": cmp_id},
    )

    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "RUN_NOT_COMPARABLE"
