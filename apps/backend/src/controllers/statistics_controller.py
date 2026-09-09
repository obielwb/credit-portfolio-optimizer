"""Routes for portfolio statistics, dashboard, history, and reports."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from src.schema import (
    SuccessResponseSchema,
    ErrorResponseSchema,
    StatisticsDashboardSchema,
    StatisticsRunSchema,
    StatisticsPortfolioResponseSchema,
    LimitsBucketSchema,
    ReturnByCohortSchema,
    ExecutionHistorySchema,
    ExecutionDetailSchema,
    StatisticsClientResultsSchema,
)
from src.services.statistics_service import (
    get_dashboard,
    get_runs_summary,
    get_portfolio,
    get_results_by_client as get_results_by_client_service,
    get_limits_buckets,
    get_return_by_month,
    get_execution_history,
    get_execution_detail,
    delete_execution,
    generate_report_pdf,
    build_run_result_csv,
)

router = APIRouter(prefix="/results", tags=["results"])


@router.get(
    "/dashboard",
    summary="Dashboard summary",
    response_model=SuccessResponseSchema,
    responses={400: {"model": ErrorResponseSchema}},
)
def dashboard(
    csv_file_id: int | None = Query(default=None),
    run_id: int | None = Query(default=None),
    page: int | None = Query(default=1, ge=1),
    page_size: int | None = Query(default=20, ge=1, le=200),
    sort_by: str | None = Query(default=None),
    sort_order: str | None = Query(default=None),
) -> dict:
    """GET /results/dashboard — dashboard summary; query: csv_file_id, run_id, page, page_size."""
    data = get_dashboard(csv_file_id, run_id, page, page_size, sort_by, sort_order)
    dto = StatisticsDashboardSchema(**data)
    return {"status": "ok", "data": dto.model_dump(), "meta": {}}


@router.get(
    "/runs", summary="Run and execution summary", response_model=SuccessResponseSchema
)
def runs_summary() -> dict:
    """GET /results/runs — aggregate run and execution summary."""
    data = get_runs_summary()
    dto = StatisticsRunSchema(**data)
    return {"status": "ok", "data": dto.model_dump(), "meta": {}}


@router.get(
    "/portfolio",
    summary="Global portfolio results",
    response_model=SuccessResponseSchema,
)
def portfolio(csv_file_id: int | None = Query(default=None)) -> dict:
    """GET /results/portfolio — global portfolio metrics; query: csv_file_id."""
    data = get_portfolio(csv_file_id)
    dto = StatisticsPortfolioResponseSchema(**data)
    return {"status": "ok", "data": dto.model_dump(), "meta": {}}


@router.get(
    "/client",
    summary="Result by client",
    response_model=SuccessResponseSchema,
)
def get_results_by_client(
    csv_file_id: int | None = Query(default=None),
    run_id: int | None = Query(default=None),
    token: str | None = Query(
        default=None, description="Client token/identifier"
    ),
) -> dict:

    data = get_results_by_client_service(csv_file_id, run_id, token)
    dto = StatisticsClientResultsSchema(**data)
    return {"status": "ok", "data": dto.model_dump(), "meta": {}}


@router.get(
    "/portfolio/limits-buckets",
    summary="Limits em buckets",
    response_model=SuccessResponseSchema,
)
def get_portfolio_buckets(csv_file_id: int | None = Query(default=None)) -> dict:
    """GET /results/portfolio/limits-buckets — limit distribution by range."""
    items = get_limits_buckets(csv_file_id)
    dto = [LimitsBucketSchema(**i).model_dump() for i in items]
    return {"status": "ok", "data": {"items": dto}, "meta": {}}


@router.get(
    "/portfolio/return-cohort",
    summary="Return by cohort",
    response_model=SuccessResponseSchema,
)
def return_by_month(
    csv_file_id: int | None = Query(default=None),
    run_id: int | None = Query(default=None),
) -> dict:

    items = get_return_by_month(csv_file_id, run_id)
    dto = [ReturnByCohortSchema(**i).model_dump() for i in items]
    return {"status": "ok", "data": {"items": dto}, "meta": {}}


@router.get(
    "/executions/history",
    summary="Paginated run history",
    response_model=SuccessResponseSchema,
)
def executions_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    status: str | None = Query(default=None),
) -> dict:
    """GET /results/executions/history — history paginado; query: page, page_size, status."""
    data = get_execution_history(page, page_size, status=status)
    dto = ExecutionHistorySchema(**data)
    return {"status": "ok", "data": dto.model_dump(), "meta": {}}


@router.get(
    "/executions/{run_id}",
    summary="Run detail for history",
    response_model=SuccessResponseSchema,
    responses={404: {"model": ErrorResponseSchema}},
)
def execution_detail(run_id: int) -> dict:

    try:
        data = get_execution_detail(run_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "RUN_NOT_FOUND", "message": str(exc)},
        ) from exc

    dto = ExecutionDetailSchema(**data)
    return {"status": "ok", "data": dto.model_dump(), "meta": {}}


@router.delete(
    "/executions/{run_id}",
    summary="Delete a run from history",
    response_model=SuccessResponseSchema,
    responses={404: {"model": ErrorResponseSchema}},
)
def execution_delete(run_id: int) -> dict:
    """DELETE /results/executions/{run_id} — delete the run and its data."""
    try:
        delete_execution(run_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "RUN_NOT_FOUND", "message": str(exc)},
        ) from exc

    return {"status": "ok", "data": {"run_id": run_id}, "meta": {}}


@router.get(
    "/executions/{run_id}/download",
    summary="Download run result CSV",
    responses={404: {"model": ErrorResponseSchema}},
)
def execution_csv_download(run_id: int) -> Response:





    try:
        content, filename = build_run_result_csv(run_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "RUN_FILE_NOT_FOUND", "message": str(exc)},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "FILE_DOWNLOAD_ERROR", "message": str(exc)},
        ) from exc

    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/report/pdf",
    summary="Generate run PDF report",
    responses={404: {"model": ErrorResponseSchema}},
)
def report_pdf(
    csv_file_id: int | None = Query(default=None),
    run_id: int | None = Query(default=None),
) -> Response:
    """GET /results/report/pdf — gera report PDF; query: csv_file_id, run_id."""
    try:
        pdf_bytes, filename = generate_report_pdf(csv_file_id, run_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "REPORT_NOT_AVAILABLE", "message": str(exc)},
        ) from exc

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
