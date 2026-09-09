import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.main import create_app
from src.utils.constants import HEALTH_STATUS_ERROR, HEALTH_STATUS_OK


@pytest.fixture()
def client():
    return TestClient(create_app())


def test_health_live_returns_ok(client):
    resp = client.get("/health/live")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["data"]["process"] == "alive"


def test_health_ready_returns_ok_when_dependencies_are_healthy(monkeypatch, client):
    monkeypatch.setattr(
        "src.controllers.health_controller.get_readiness",
        lambda: {
            "status": HEALTH_STATUS_OK,
            "database": HEALTH_STATUS_OK,
            "queue": HEALTH_STATUS_OK,
            "storage": HEALTH_STATUS_OK,
            "dependencies": [HEALTH_STATUS_OK, HEALTH_STATUS_OK, HEALTH_STATUS_OK],
        },
    )

    resp = client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["data"]["database"] == "ok"
    assert body["data"]["queue"] == "ok"
    assert body["data"]["storage"] == "ok"


def test_health_ready_returns_503_when_dependency_fails(monkeypatch, client):
    monkeypatch.setattr(
        "src.controllers.health_controller.get_readiness",
        lambda: {
            "status": HEALTH_STATUS_ERROR,
            "database": HEALTH_STATUS_OK,
            "queue": HEALTH_STATUS_ERROR,
            "storage": HEALTH_STATUS_OK,
            "dependencies": [
                HEALTH_STATUS_OK,
                HEALTH_STATUS_ERROR,
                HEALTH_STATUS_OK,
            ],
        },
    )

    resp = client.get("/health/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "error"
    assert body["data"]["queue"] == "error"


def test_get_readiness_aggregates_component_checks(monkeypatch):
    import src.services.health_service as health_service

    monkeypatch.setattr(health_service, "check_database", lambda: HEALTH_STATUS_OK)
    monkeypatch.setattr(health_service, "check_queue", lambda: HEALTH_STATUS_OK)
    monkeypatch.setattr(health_service, "check_storage", lambda: HEALTH_STATUS_OK)

    readiness = health_service.get_readiness()
    assert readiness["status"] == HEALTH_STATUS_OK
    assert readiness["dependencies"] == [
        HEALTH_STATUS_OK,
        HEALTH_STATUS_OK,
        HEALTH_STATUS_OK,
    ]


def test_check_database_returns_error_when_connection_fails(monkeypatch):
    import src.services.health_service as health_service

    def _fail_engine(*_args, **_kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(health_service, "build_engine", _fail_engine)
    assert health_service.check_database() == HEALTH_STATUS_ERROR


def test_check_queue_returns_ok_for_mock_mode(monkeypatch):
    import src.services.health_service as health_service

    monkeypatch.setenv("ASYNC_QUEUE_USE_MOCK", "true")
    assert health_service.check_queue() == HEALTH_STATUS_OK


def test_check_storage_health_returns_unknown_without_env(monkeypatch):
    import src.utils.minio as minio_utils

    for env_name in (
        "MINIO_ENDPOINT",
        "MINIO_ACCESS_KEY",
        "MINIO_SECRET_KEY",
        "MINIO_BUCKET",
        "MINIO_SECURE",
        "MINIO_ROOT_PREFIX",
    ):
        monkeypatch.delenv(env_name, raising=False)

    assert minio_utils.check_storage_health() == "unknown"
