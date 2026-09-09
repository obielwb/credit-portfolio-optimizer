"""Service for comparing completed runs."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.models.comparison import ComparisonRuns, RunResultSummary
from src.repositories import ComparisonRepository
from src.services.parameters_service import _orm_to_dict
from src.services.cohort_analytics import (
    build_cohort_analysis,
    build_return_by_cohort,
    resolve_return_grouping,
)
from src.services.statistics_service import (
    _calc_approval_rate,
    get_limits_buckets_from_clients,
)
from src.utils.db.session import get_db_session


class ComparisonError(ValueError):


    code: str = "COMPARISON_ERROR"

    def __init__(self, message: str) -> None:

        super().__init__(message)


class SameRunComparisonError(ComparisonError):
    """Raised when a run is compared with itself."""

    code = "SAME_RUN_COMPARISON"


class RunNotFoundForComparisonError(ComparisonError):


    code = "RUN_NOT_FOUND"


class RunNotComparableError(ComparisonError):


    code = "RUN_NOT_COMPARABLE"


def get_run_snapshot(run_id: int) -> dict[str, Any]:


    with get_db_session() as session:
        repo = ComparisonRepository(session)
        run = repo.get_run_with_context(run_id)
        _ensure_run_has_result(run, run_id)

        clients = repo.get_clients_by_run(run_id)
        summary = _build_summary(run, run.result, clients)
        return _build_snapshot(run, clients, summary)


def compare_runs(reference_run_id: int, compared_run_id: int) -> dict[str, Any]:


    if reference_run_id == compared_run_id:
        raise SameRunComparisonError("A run cannot be compared with itself")

    with get_db_session() as session:
        repo = ComparisonRepository(session)

        ref_run = repo.get_run_with_context(reference_run_id)
        cmp_run = repo.get_run_with_context(compared_run_id)
        _ensure_run_is_comparable(ref_run, reference_run_id)
        _ensure_run_is_comparable(cmp_run, compared_run_id)

        ref_clients = repo.get_clients_by_run(reference_run_id)
        cmp_clients = repo.get_clients_by_run(compared_run_id)
        ref_summary = _build_summary(ref_run, ref_run.result, ref_clients)
        cmp_summary = _build_summary(cmp_run, cmp_run.result, cmp_clients)
        comparison = ComparisonRuns(reference=ref_summary, compared=cmp_summary)

        return {
            "reference": _build_snapshot(ref_run, ref_clients, ref_summary),
            "compared": _build_snapshot(cmp_run, cmp_clients, cmp_summary),
            "deltas": _build_deltas(comparison),
        }


def _ensure_run_has_result(run, run_id: int) -> None:

    if run is None:
        raise RunNotFoundForComparisonError(f"Run {run_id} not found")
    if run.result is None:
        raise RunNotComparableError(f"Run {run_id} has no result")


def _ensure_run_is_comparable(run, run_id: int) -> None:

    _ensure_run_has_result(run, run_id)
    if run.status != "success":
        raise RunNotComparableError(
            f"Run {run_id} did not complete successfully (status={run.status})"
        )


def _build_summary(run, result, clients) -> RunResultSummary:


    file = run.file_csv
    # Prefer the stored approval_rate (set at run completion) so historical runs
    # remain correct after their clients are overwritten by newer runs.
    stored_rate = getattr(result, "approval_rate", None)
    approval_rate = (
        Decimal(str(stored_rate)) if stored_rate is not None
        else _calc_approval_rate(clients)
    )
    return RunResultSummary(
        run_id=run.id,
        algorithm=run.algorithm,
        created_at=run.created_at,
        total_clients=int(result.total_clients),
        total_limit=Decimal(str(result.total_limit)),
        total_income=Decimal(str(result.total_income)),
        total_loss=Decimal(str(result.total_loss)),
        total_return=Decimal(str(result.total_return)),
        financial_default_rate=Decimal(str(result.financial_default_rate)),
        approval_rate=approval_rate,
        csv_file_id=run.csv_file_id,
        file_name=file.name if file is not None else None,
    )


def _build_snapshot(run, clients, summary: RunResultSummary) -> dict[str, Any]:


    file = run.file_csv
    clusters = list(getattr(run, "clusters", []) or [])
    total_return = float(summary.total_return)

    return {
        "run_id": run.id,
        "algorithm": run.algorithm,
        "status": run.status,
        "created_at": run.created_at,
        "execution_time_ms": run.execution_time_ms,
        "csv_file_id": run.csv_file_id,
        "file_name": file.name if file is not None else "",
        "parameters": _orm_to_dict(run.parameters),
        "metrics": {
            "total_clients": summary.total_clients,
            "total_limit": float(summary.total_limit),
            "total_income": float(summary.total_income),
            "total_loss": float(summary.total_loss),
            "total_return": total_return,
            "financial_default_rate": float(summary.financial_default_rate),
            "approval_rate": float(summary.approval_rate),
        },
        "limit_ranges": get_limits_buckets_from_clients(clients),
        "return_by_cohort": build_return_by_cohort(clusters, clients, total_return),
        "cohort_analysis": build_cohort_analysis(clusters, clients),
        "return_grouping": resolve_return_grouping(clusters, clients),
    }


def _build_deltas(comparison: ComparisonRuns) -> dict[str, Any]:


    reference = comparison.reference
    compared = comparison.compared

    return {
        "total_limit": _delta_item(compared.total_limit, reference.total_limit),
        "approval_rate": _delta_item(
            compared.approval_rate,
            reference.approval_rate,
        ),
        "total_return": _delta_item(
            compared.total_return,
            reference.total_return,
        ),
        "financial_default_rate": _delta_item(
            compared.financial_default_rate,
            reference.financial_default_rate,
        ),
        "total_clients": _delta_item(
            Decimal(compared.total_clients),
            Decimal(reference.total_clients),
        ),
        "total_income": _delta_item(compared.total_income, reference.total_income),
        "total_loss": _delta_item(compared.total_loss, reference.total_loss),
    }


def _delta_item(compared: Decimal, reference: Decimal) -> dict[str, float | None]:

    absoluto = float(compared - reference)
    if reference == 0:
        return {"absoluto": absoluto, "percentage": None}
    percentage = float((compared - reference) / reference * 100)
    return {"absoluto": absoluto, "percentage": percentage}


__all__ = [
    "ComparisonError",
    "SameRunComparisonError",
    "RunNotFoundForComparisonError",
    "RunNotComparableError",
    "compare_runs",
    "get_run_snapshot",
]
