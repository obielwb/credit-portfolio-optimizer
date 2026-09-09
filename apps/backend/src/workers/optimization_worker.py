

from __future__ import annotations

import asyncio
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any

from src.schema import OptimizationJobSchema
from src.repositories import ParametersRepository
from src.services.async_service import DEFAULT_ASYNC_QUEUE_SERVICE, AsyncQueueService
from src.services.client_pipeline_input import load_clients_for_job
from src.services.optimization_service import (
    _extract_run_id,
    complete_run,
    fail_run,
    get_status,
    is_run_already_completed,
    mark_run_processing,
    update_run_progress,
)
from src.models.run import RunState
from src.utils.algorithm_path import ensure_algorithm_path
from src.utils.db.session import get_db_session


def _ensure_algorithm_path() -> None:

    ensure_algorithm_path()


def _load_pipeline_modules() -> tuple[Any, Any]:
    """Import the algorithm pipeline and models on demand."""

    _ensure_algorithm_path()

    from models import ModelParameters  # type: ignore import-not-found
    from pipeline import run_pipeline  # type: ignore import-not-found

    return ModelParameters, run_pipeline


def _build_parameters_model(job: OptimizationJobSchema) -> Any:


    ModelParameters, _ = _load_pipeline_modules()

    with get_db_session() as session:
        params_repo = ParametersRepository(session)
        if job.parameters_id is not None:
            params = params_repo.get_by_id(job.parameters_id)
            if params is None:
                raise ValueError(f"Parameters id={job.parameters_id} were not found.")
        else:
            params = params_repo.get_latest_or_raise()

        return ModelParameters(
            interchange=float(params.interchange),
            lgd=float(params.lgd),
            min_limit=float(params.min_limit),
            max_rejected_limit=float(params.max_rejected_limit),
            max_limit=float(params.max_limit),
            baseline_default_rate=float(params.baseline_default_rate),
            limit_step=50.0,
            utilization_rate=float(params.utilization_rate),
            enabled=bool(params.enabled),
            n_clusters=int(params.n_clusters) if params.n_clusters is not None else None,
            max_clients_per_cluster=int(params.max_clients_per_cluster),
            min_clusters=int(params.min_clusters),
            filter=bool(params.filter),
        )


def _process_job(job: OptimizationJobSchema) -> dict[str, Any]:






    _ensure_algorithm_path()
    from progress import set_progress_callback  # type: ignore import-not-found

    def _on_algorithm_progress(state: str) -> None:
        """Algorithm progress callback that updates run state."""
        update_run_progress(job.run_id, state, start=True)

    _, run_pipeline = _load_pipeline_modules()
    parameters = _build_parameters_model(job)
    clients = load_clients_for_job(job)

    set_progress_callback(_on_algorithm_progress)
    try:
        result = run_pipeline(
            None,
            job.algorithm,
            parameters,
            clients=clients,
        )
    finally:
        set_progress_callback(None)

    update_run_progress(job.run_id, RunState.VALIDATING_CONSTRAINTS, start=True)

    clusters_payload = [
        asdict(cluster) if is_dataclass(cluster) else cluster
        for cluster in getattr(result, "clusters", ())
    ]

    return {
        "run_id": job.run_id,
        "final_status": "success",
        "algorithm": job.algorithm,
        "result_id": job.run_id,
        "client_tokens": list(job.client_tokens),
        "parameters_id": job.parameters_id,
        "result_portfolio": asdict(result),
        "clusters": clusters_payload,
        "client_count": len(result.clients),
        "total_limit": result.total_limit,
        "total_return": result.total_return,
        "total_loss": result.total_loss,
        "financial_default_rate": result.financial_default_rate,
        "processado_em": datetime.now(),
    }


async def handle_optimization_message(payload: dict[str, Any]) -> None:


    run_id = _extract_run_id(payload)
    job: OptimizationJobSchema | None = None

    try:
        job = OptimizationJobSchema.model_validate(payload)
        run_id = job.run_id
        if is_run_already_completed(job.run_id):
            return
        mark_run_processing(job.run_id)
        result = await asyncio.to_thread(_process_job, job)
        complete_run(job.run_id, result)
    except Exception as exc:
        if run_id is not None:
            fail_run(run_id, str(exc), stage="worker")
        raise


async def run_optimization_worker(
    queue_service: AsyncQueueService | None = None,
    *,
    max_messages: int | None = None,
    continuous: bool = False,
) -> int:





    service = queue_service or DEFAULT_ASYNC_QUEUE_SERVICE
    return await service.consume_optimization_jobs(
        handle_optimization_message,
        max_messages=max_messages,
        block=continuous,
    )


async def process_run(run_id: int) -> dict[str, Any] | None:


    status = get_status(run_id)
    if not status:
        return None

    job_data = status.get("job")
    if not job_data:
        return None

    await handle_optimization_message(job_data)
    return get_status(run_id)
