"""Routes for optimization run status and results."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.schema import RunStatusSchema, RunResultSchema
from src.services.optimization_service import get_result, get_status

router = APIRouter(prefix="/optimization", tags=["optimization"])


@router.get(
    "/runs/{run_id}", summary="Get run status", response_model=RunStatusSchema
)
def get_run_status(run_id: int) -> RunStatusSchema:
    """GET /optimization/runs/{run_id} — return status and the run's current stage."""
    run = get_status(run_id)
    if not run:
        raise HTTPException(
            status_code=404,
            detail={"code": "RUN_NOT_FOUND", "message": "Run not found"},
        )
    return RunStatusSchema(**run)


@router.get(
    "/runs/{run_id}/result",
    summary="Consulta result final",
    response_model=RunResultSchema,
)
def get_run_result(run_id: int) -> RunResultSchema:

    result = get_result(run_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail={"code": "RESULT_NOT_FOUND", "message": "Result not found"},
        )
    return RunResultSchema(**result)
