"""Routes for comparing completed runs."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.schema import (
    ComparisonRunsDataSchema,
    ErrorResponseSchema,
    RunComparisonSnapshotSchema,
    SuccessResponseSchema,
)
from src.services.comparison_service import (
    ComparisonError,
    RunNotComparableError,
    RunNotFoundForComparisonError,
    SameRunComparisonError,
    compare_runs,
    get_run_snapshot,
)

router = APIRouter(prefix="/comparison", tags=["comparison"])


def _http_exception_from_comparison_error(exc: ComparisonError) -> HTTPException:

    status_code = 400
    if isinstance(exc, RunNotFoundForComparisonError):
        status_code = 404
    elif isinstance(exc, RunNotComparableError):
        status_code = 409

    return HTTPException(
        status_code=status_code,
        detail={"code": exc.__class__.code, "message": str(exc)},
    )


@router.get(
    "/runs",
    summary="Compare duas runs completed",
    response_model=SuccessResponseSchema,
    responses={
        400: {"model": ErrorResponseSchema},
        404: {"model": ErrorResponseSchema},
        409: {"model": ErrorResponseSchema},
    },
)
def compare_runs_endpoint(
    reference_run_id: int = Query(..., ge=1),
    compared_run_id: int = Query(..., ge=1),
) -> dict:
    """GET /comparison/runs — compares duas runs; query: reference_run_id, compared_run_id."""
    try:
        data = compare_runs(reference_run_id, compared_run_id)
    except ComparisonError as exc:
        raise _http_exception_from_comparison_error(exc) from exc

    dto = ComparisonRunsDataSchema(**data)
    return {"status": "ok", "data": dto.model_dump(), "meta": {}}


@router.get(
    "/runs/{run_id}",
    summary="Run snapshot for comparison",
    response_model=SuccessResponseSchema,
    responses={
        404: {"model": ErrorResponseSchema},
        409: {"model": ErrorResponseSchema},
    },
)
def get_run_snapshot_endpoint(run_id: int) -> dict:

    try:
        data = get_run_snapshot(run_id)
    except ComparisonError as exc:
        raise _http_exception_from_comparison_error(exc) from exc

    dto = RunComparisonSnapshotSchema(**data)
    return {"status": "ok", "data": dto.model_dump(), "meta": {}}
