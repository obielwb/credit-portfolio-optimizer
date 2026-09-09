

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

from sqlalchemy import text

from src.services.async_service import build_async_queue_config
from src.utils.constants import (
    HEALTH_STATUS_ERROR,
    HEALTH_STATUS_OK,
    HEALTH_STATUS_UNKNOWN,
)
from src.utils.db.connection import build_engine
from src.utils.minio import check_storage_health
from src.utils.rabbitmq import get_rabbitmq_heartbeat

HealthComponentStatus = str

_QUEUE_HEALTH_CACHE_TTL_SECONDS = max(
    10,
    int(os.getenv("HEALTH_QUEUE_CACHE_TTL_SECONDS", "60")),
)
_queue_health_cache: tuple[float, HealthComponentStatus] | None = None


def check_database() -> HealthComponentStatus:
    """Run SELECT 1 against the configured PostgreSQL database."""

    try:
        engine = build_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return HEALTH_STATUS_OK
    except Exception:
        return HEALTH_STATUS_ERROR


async def _check_queue_async() -> HealthComponentStatus:

    config = build_async_queue_config()
    if config.use_mock:
        return HEALTH_STATUS_OK

    try:
        import aio_pika

        connection = await aio_pika.connect_robust(
            config.amqp_url,
            timeout=5,
            heartbeat=get_rabbitmq_heartbeat(),
        )
        async with connection:
            channel = await connection.channel()
            await channel.close()
        return HEALTH_STATUS_OK
    except Exception:
        return HEALTH_STATUS_ERROR


def check_queue() -> HealthComponentStatus:






    global _queue_health_cache

    now = time.monotonic()
    if (
        _queue_health_cache is not None
        and now - _queue_health_cache[0] < _QUEUE_HEALTH_CACHE_TTL_SECONDS
    ):
        return _queue_health_cache[1]

    status = asyncio.run(_check_queue_async())
    _queue_health_cache = (now, status)
    return status


def check_storage() -> HealthComponentStatus:


    return check_storage_health()


def get_readiness() -> dict[str, Any]:


    database = check_database()
    queue = check_queue()
    storage = check_storage()
    dependencies = [database, queue, storage]

    if all(status == HEALTH_STATUS_OK for status in dependencies):
        overall = HEALTH_STATUS_OK
    elif any(status == HEALTH_STATUS_ERROR for status in dependencies):
        overall = HEALTH_STATUS_ERROR
    else:
        overall = HEALTH_STATUS_ERROR

    return {
        "status": overall,
        "database": database,
        "queue": queue,
        "storage": storage,
        "dependencies": dependencies,
    }


__all__ = [
    "check_database",
    "check_queue",
    "check_storage",
    "get_readiness",
]
