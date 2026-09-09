

from __future__ import annotations

import os


def build_rabbitmq_url() -> str:


    host = _require_env("RABBITMQ_HOST")
    port = _require_env("RABBITMQ_PORT")
    user = _require_env("RABBITMQ_USER")
    password = _require_env("RABBITMQ_PASSWORD")
    vhost = _require_env("RABBITMQ_VHOST")

    if not vhost.startswith("/"):
        vhost = f"/{vhost}"

    return f"amqp://{user}:{password}@{host}:{port}{vhost}"


def get_optimization_queue_name() -> str:


    return _require_env("RABBITMQ_QUEUE_OPTIMIZATION")


def get_rabbitmq_heartbeat() -> int:
    """AMQP heartbeat interval in seconds; long jobs require a high value."""

    raw = os.getenv("RABBITMQ_HEARTBEAT", "600")
    try:
        heartbeat = int(raw)
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid RABBITMQ_HEARTBEAT: {raw!r}. Use an integer number of seconds."
        ) from exc
    return max(60, heartbeat)


def _require_env(name: str) -> str:
    """Read a required environment variable or raise RuntimeError."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value
