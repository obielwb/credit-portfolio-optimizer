

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src.schema import (
    ParametersSchema,
    ParametersUpdateRequestSchema,
    SuccessResponseSchema,
    ErrorResponseSchema,
)
from src.services.parameters_service import get_active, update_active, list_versions

router = APIRouter(prefix="/parameters", tags=["parameters"])


@router.get(
    "/active",
    summary="Return the active parameters",
    response_model=SuccessResponseSchema,
    responses={404: {"model": ErrorResponseSchema}},
)
def get_active_params() -> dict:

    active = get_active()
    if not active:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "PARAMETERS_NOT_FOUND",
                "message": "Active parameters were not found",
            },
        )
    params = ParametersSchema(**active)
    return {"status": "ok", "data": params.model_dump(), "meta": {}}


@router.put(
    "/active",
    summary="Create or update the active parameters",
    response_model=SuccessResponseSchema,
    responses={400: {"model": ErrorResponseSchema}},
)
def update_active_params(payload: ParametersUpdateRequestSchema) -> dict:
    """PUT /parameters/active — cria or updates parameters; body: ParametersUpdateRequestSchema."""
    existing = get_active() or {}

    incoming = payload.model_dump(exclude_unset=True)
    updates = dict(incoming)

    merged = {**existing, **updates}

    required = [
        "utilization_rate",
        "lgd",
        "min_pd",
        "max_pd",
        "filter",
        "max_limit",
        "baseline_default_rate",
        "min_limit",
        "discretize",
        "interchange",
        "max_rejected_limit",
        "enabled",
        "n_clusters",
        "max_clients_per_cluster",
        "min_clusters",
        "multipliers",
    ]
    if not existing:
        missing = [k for k in required if k not in merged or merged.get(k) is None]
        if missing:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "code": "MISSING_REQUIRED_PARAMETERS",
                    "message": "Required parameters are missing for the active version.",
                    "details": {"missing": missing},
                },
            )

    record = update_active(merged)
    params = ParametersSchema(**record)
    return {"status": "ok", "data": params.model_dump(), "meta": {}}
