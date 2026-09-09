"""Rotas de health, readiness e liveness do backend."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Response

from src.schema import HealthResponseSchema
from src.services.health_service import get_readiness
from src.utils import (
    HEALTH_PROCESS_STATUS_ALIVE,
    HEALTH_STATUS_OK,
    HEALTH_UPTIME_PLACEHOLDER,
    SERVICE_NAME,
    SERVICE_VERSION,
)

router = APIRouter(prefix="/health", tags=["health"])


def _utc_now() -> str:

    return datetime.now().isoformat()


def _base_payload(
    status: str, *, details: dict[str, object] | None = None
) -> dict[str, object]:
    """Build the default health-check response payload."""
    payload: dict[str, object] = {
        "status": status,
        "data": {
            "service": SERVICE_NAME,
            "version": SERVICE_VERSION,
            "timestamp": _utc_now(),
        },
    }
    if details:
        payload["data"] = {**payload["data"], **details}
    return payload


@router.get("", summary="Health check", response_model=HealthResponseSchema)
def get_health() -> dict[str, object]:
    """GET /health — verifica se o servico esta respondendo."""
    return _base_payload(
        HEALTH_STATUS_OK,
        details={
            "uptime": HEALTH_UPTIME_PLACEHOLDER,
        },
    )


@router.get("/ready", summary="Readiness check", response_model=HealthResponseSchema)
def get_ready(response: Response) -> dict[str, object]:

    readiness = get_readiness()
    if readiness["status"] != HEALTH_STATUS_OK:
        response.status_code = 503

    return _base_payload(
        readiness["status"],
        details={
            "database": readiness["database"],
            "queue": readiness["queue"],
            "storage": readiness["storage"],
            "dependencies": readiness["dependencies"],
        },
    )


@router.get("/live", summary="Liveness check", response_model=HealthResponseSchema)
def get_live() -> dict[str, object]:

    return _base_payload(
        HEALTH_STATUS_OK,
        details={
            "process": HEALTH_PROCESS_STATUS_ALIVE,
        },
    )
