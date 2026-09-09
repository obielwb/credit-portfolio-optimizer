import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.main import create_app


@pytest.fixture()
def app():
    return create_app()


def test_create_app_registers_domain_routers(app):
    paths = {getattr(route, "path", None) for route in app.routes}

    assert "/health" in paths
    assert "/health/ready" in paths
    assert "/health/live" in paths
    assert "/ingestion/upload" in paths
    assert "/optimization/runs/{run_id}" in paths
    assert "/optimization/runs/{run_id}/result" in paths
    assert "/parameters/active" in paths
    assert "/comparison/runs" in paths
    assert "/comparison/runs/{run_id}" in paths
    assert "/results/dashboard" in paths
    assert "/" in paths


def test_create_app_does_not_expose_manual_run_trigger(app):
    paths = {getattr(route, "path", None) for route in app.routes}
    assert "/optimization/runs" not in paths


def test_create_app_registers_cors_middleware(app):
    from starlette.middleware.cors import CORSMiddleware

    assert any(middleware.cls is CORSMiddleware for middleware in app.user_middleware)
