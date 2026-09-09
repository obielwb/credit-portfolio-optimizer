import asyncio
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from src.services.async_service import AsyncQueueConfig, AsyncQueueService
from src.utils import build_rabbitmq_url, get_optimization_queue_name


def _rabbitmq_integration_enabled() -> bool:
    return os.getenv("RUN_RABBITMQ_INTEGRATION", "").lower() in {"1", "true", "yes"}


@pytest.fixture()
def rabbitmq_service(monkeypatch):
    monkeypatch.setenv("RABBITMQ_HOST", os.getenv("RABBITMQ_HOST", "localhost"))
    monkeypatch.setenv("RABBITMQ_PORT", os.getenv("RABBITMQ_PORT", "5672"))
    monkeypatch.setenv("RABBITMQ_USER", os.getenv("RABBITMQ_USER", "guest"))
    monkeypatch.setenv("RABBITMQ_PASSWORD", os.getenv("RABBITMQ_PASSWORD", "guest"))
    monkeypatch.setenv("RABBITMQ_VHOST", os.getenv("RABBITMQ_VHOST", "/"))
    queue_name = f"optimization-test-{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("RABBITMQ_QUEUE_OPTIMIZATION", queue_name)

    return AsyncQueueService(
        AsyncQueueConfig(
            amqp_url=build_rabbitmq_url(),
            queue_name=get_optimization_queue_name(),
            use_mock=False,
        )
    )


@pytest.mark.skipif(not _rabbitmq_integration_enabled(), reason="RabbitMQ local not habilitado (RUN_RABBITMQ_INTEGRATION=1)")
def test_publish_and_consume_via_rabbitmq(rabbitmq_service):
    payload = {
        "run_id": 42,
        "algorithm": "simplex",
        "parameters_id": 1,
        "client_tokens": ["token-a", "token-b"],
    }
    received: list[dict] = []

    async def handler(message: dict) -> None:
        received.append(message)

    async def run_flow() -> None:
        await rabbitmq_service.publish_optimization_job(payload)
        processed = await rabbitmq_service.consume_optimization_jobs(
            handler,
            max_messages=1,
        )
        assert processed == 1

    asyncio.run(run_flow())
    assert received == [payload]


def test_build_async_queue_config_respects_env(monkeypatch):
    monkeypatch.setenv("ASYNC_QUEUE_USE_MOCK", "false")
    from src.services.async_service import build_async_queue_config

    config = build_async_queue_config()
    assert config.use_mock is False

    monkeypatch.setenv("ASYNC_QUEUE_USE_MOCK", "true")
    config = build_async_queue_config()
    assert config.use_mock is True
