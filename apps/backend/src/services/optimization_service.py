
























from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.schema import OptimizationJobSchema
from src.models.run import ETAPA_LABELS, RunState, RunStatus
from src.repositories import ParametersRepository, RunRepository
from src.repositories import (
    ResultRepository,
    ClientRepository,
    ClientHistoryRepository,
    RunClusterRepository,
)
from src.services.async_service import DEFAULT_ASYNC_QUEUE_SERVICE
from src.custom_types import ClientChangeType
from src.utils.db.session import get_db_session

from src.utils.algorithm import AVAILABLE_ALGORITHMS

AVAILABLE_ALGORITHMS = set(AVAILABLE_ALGORITHMS)


def _format_run_failure_message(
    error: str | None,
    *,
    stage: str | None = None,
) -> str | None:

    if stage and error:
        return f"[{stage}] {error}"
    if stage:
        return f"[{stage}] unknown failure"
    return error


def _compute_run_duration_ms(run: Any, *, end_at: datetime | None = None) -> int:


    end = end_at or datetime.now(timezone.utc)
    start = run.started_at or run.created_at
    if start is None:
        return 0

    # SQLite strips tzinfo on round-trip; assume naive datetimes are UTC
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    elapsed = (end - start).total_seconds()
    return max(0, int(elapsed * 1000))


def fail_run(
    run_id: int,
    error: str | None = None,
    *,
    stage: str | None = None,
) -> None:
    """Mark the run as failed and expose the reason through `get_status`."""

    message = _format_run_failure_message(error, stage=stage)
    with get_db_session() as session:
        run_repo = RunRepository(session)
        run = run_repo.get_by_id(run_id)
        if run is None or run.status == RunStatus.SUCCESS.value:
            return
        time_ms = _compute_run_duration_ms(run)
        run_repo.mark_error(run_id, time_ms=time_ms, error_reason=message)

    update_run_progress(
        run_id,
        RunState.FAILED,
        finish=True,
    )


def update_run_progress(
    run_id: int,
    state: RunState | str,
    *,
    finish: bool = False,
    start: bool = False,
) -> None:


    state_enum = state if isinstance(state, RunState) else RunState(state)
    now = datetime.now()

    with get_db_session() as session:
        run_repo = RunRepository(session)
        run = run_repo.get_by_id(run_id)
        if run is None:
            return

        started_at = run.started_at
        if start and started_at is None:
            started_at = now

        finished_at = now if finish else None
        run_repo.update_progress(
            run_id,
            state_operacional=state_enum.value,
            started_at=started_at,
            finished_at=finished_at,
        )


def _extract_run_id(payload: dict[str, Any]) -> int | None:
    """Extract run_id from a queue-message payload."""
    run_id = payload.get("run_id")
    if isinstance(run_id, int):
        return run_id
    if isinstance(run_id, str) and run_id.isdigit():
        return int(run_id)
    return None


# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------


async def enqueue_run_for_processing(
    run_id: int,
    algorithm: str = "simplex",
    client_tokens: list[str] | None = None,
    parameters_id: int | None = None,
) -> dict[str, Any]:




    if algorithm not in AVAILABLE_ALGORITHMS:
        raise ValueError(
            f"Algorithm '{algorithm}' is invalid. "
            f"Options: {', '.join(sorted(AVAILABLE_ALGORITHMS))}"
        )

    tokens = list(client_tokens or [])

    try:
        with get_db_session() as session:
            params_repo = ParametersRepository(session)
            run_repo = RunRepository(session)

            run = run_repo.get_by_id(run_id)
            if not run:
                raise ValueError(f"Run id={run_id} was not found.")

            if parameters_id is not None:
                params = params_repo.get_by_id(parameters_id)
                if not params:
                    raise ValueError(f"Parameters id={parameters_id} were not found.")
                resolved_parameters_id = params.id
            else:
                resolved_parameters_id = run.parameters_id

            updates: dict[str, Any] = {}
            if run.algorithm != algorithm:
                updates["algorithm"] = algorithm
            if run.parameters_id != resolved_parameters_id:
                updates["parameters_id"] = resolved_parameters_id
            if updates:
                run_repo.update_by_id(run_id, updates)

        job = OptimizationJobSchema(
            run_id=run_id,
            algorithm=algorithm,
            client_tokens=tokens,
            parameters_id=resolved_parameters_id,
        )
        publish_result = await DEFAULT_ASYNC_QUEUE_SERVICE.publish_optimization_job(job)
    except Exception as exc:
        fail_run(run_id, str(exc), stage="enfileiramento")
        raise

    return {
        "run_id": run_id,
        "job": job.model_dump(),
        "queue": publish_result["queue"],
    }


def get_status(run_id: int) -> dict[str, Any] | None:




    with get_db_session() as session:
        run_repo = RunRepository(session)
        run = run_repo.get_by_id(run_id)
        if not run:
            return None

        return _build_status_payload(run)


def _build_status_payload(run: Any) -> dict[str, Any]:

    state_value = run.state_operacional or RunState.WAITING_FOR_PROCESSING.value
    try:
        state_enum = RunState(state_value)
    except ValueError:
        state_enum = RunState.WAITING_FOR_PROCESSING

    if run.status == RunStatus.SUCCESS.value and run.result is not None:
        state_enum = RunState.COMPLETED

    if run.status in {RunStatus.ERROR.value, RunStatus.TIMEOUT.value}:
        state_enum = RunState.FAILED

    return {
        "run_id": run.id,
        "state": state_enum.value,
        "current_stage": ETAPA_LABELS.get(state_enum, state_enum.value),
        "started_at": run.started_at or run.created_at,
        "finished_at": run.finished_at
        or (run.result.created_at if run.result else None),
        "error": run.error_reason
        if run.status in {RunStatus.ERROR.value, RunStatus.TIMEOUT.value}
        else None,
    }


def get_result(run_id: int) -> dict[str, Any] | None:




    with get_db_session() as session:
        run_repo = RunRepository(session)
        run = run_repo.get_by_id(run_id)
        if not run or not run.result:
            return None

        return {
            "run_id": run.id,
            "final_status": run.status,
            "algorithm": run.algorithm,
            "result_id": run.result.id,
            "error": run.error_reason,
            "released_at": run.result.created_at,
        }


def update_run_status(
    run_id: int,
    status: str,
    execution_time_ms: int = 0,
    *,
    error_reason: str | None = None,
) -> None:




    if status == RunStatus.ERROR.value or status.lower() == "error":
        fail_run(run_id, error_reason, stage="status")
        if execution_time_ms:
            with get_db_session() as session:
                RunRepository(session).update_by_id(
                    run_id, {"execution_time_ms": execution_time_ms}
                )
        return

    with get_db_session() as session:
        run_repo = RunRepository(session)
        if status == RunStatus.SUCCESS.value or status.lower() == "success":
            run_repo.mark_success(run_id, execution_time_ms)
        elif status == RunStatus.TIMEOUT.value or status.lower() == "timeout":
            fail_run(run_id, error_reason or "timeout", stage="status")
            if execution_time_ms:
                run_repo.update_by_id(run_id, {"execution_time_ms": execution_time_ms})
        else:
            run_repo.update_by_id(
                run_id,
                {
                    "status": status,
                    "execution_time_ms": execution_time_ms,
                },
            )


def mark_run_processing(run_id: int) -> None:
    """Mark the start of asynchronous worker processing."""

    update_run_progress(
        run_id,
        RunState.CALCULATING_CONSTRAINTS,
        start=True,
    )


def is_run_already_completed(run_id: int) -> bool:


    with get_db_session() as session:
        run_repo = RunRepository(session)
        result_repo = ResultRepository(session)
        run = run_repo.get_by_id(run_id)
        if run is None:
            return False
        return (
            run.status == RunStatus.SUCCESS.value
            and result_repo.get_by_run_id(run_id) is not None
        )


def complete_run(run_id: int, result_payload: dict[str, Any]) -> None:






    from src.schema.database.portfolio_results import PortfolioResults as ResultsORM

    if is_run_already_completed(run_id):
        return

    with get_db_session() as session:
        run_repo = RunRepository(session)
        result_repo = ResultRepository(session)
        client_repo = ClientRepository(session)
        history_repo = ClientHistoryRepository(session)
        run_cluster_repo = RunClusterRepository(session)

        # Persiste result agregado
        result_portfolio = result_payload.get("result_portfolio", {})
        result_values = {
            "total_clients": int(
                result_portfolio.get(
                    "total_clients", result_payload.get("client_count", 0)
                )
            ),
            "total_limit": result_portfolio.get(
                "total_limit", result_payload.get("total_limit", 0)
            ),
            "total_income": result_portfolio.get("total_income", 0),
            "total_loss": result_portfolio.get(
                "total_loss", result_payload.get("total_loss", 0)
            ),
            "total_return": result_portfolio.get(
                "total_return", result_payload.get("total_return", 0)
            ),
            "financial_default_rate": result_portfolio.get(
                "financial_default_rate",
                result_payload.get("financial_default_rate", 0),
            ),
            "baseline_default_rate": result_portfolio.get(
                "baseline_default_rate", 0
            ),
        }
        # Compute and store approval_rate + approved now, while we still have
        # per-client limits. After this run, upsert_client overwrites last_run_id
        # for all clients, so dynamic queries for old runs would return 0% approval.
        clients_result = result_portfolio.get("clients", [])
        total_c = len(clients_result)
        approved_c = sum(
            1 for c in clients_result if float(c.get("suggested_limit", 0)) > 0
        )
        result_values["approved"] = approved_c
        result_values["approval_rate"] = (
            approved_c / total_c if total_c > 0 else 0
        )
        existing_result = result_repo.get_by_run_id(run_id)
        if existing_result is None:
            result_repo.create(
                ResultsORM(run_id=run_id, **result_values)
            )
        else:
            result_repo.update_by_id(existing_result.id, result_values)




        # load prior states with a few SELECTs and bulk-write clients and audit entries,

        clients = result_portfolio.get("clients", [])


        por_token: dict[str, dict[str, Any]] = {}
        for r in clients:
            client = r.get("client", {})
            token = str(client.get("token"))
            por_token[token] = {
                "limit": r.get("suggested_limit", 0),
                "capacity": client.get("payment_capacity", 0),
                "score": client.get(
                    "contract_propensity_score", client.get("propensity_score", 0)
                ),
                "pd": client.get("product_pd", client.get("pd", 0)),
            }

        states = client_repo.fetch_states_by_tokens(list(por_token.keys()))

        client_inserts: list[dict[str, Any]] = []
        client_updates: list[dict[str, Any]] = []
        audit_rows: list[dict[str, Any]] = []
        for token, data in por_token.items():
            limit = data["limit"]
            values = {
                "last_run_id": run_id,
                "last_suggested_limit": limit,
                "payment_capacity": data["capacity"],
                "score": data["score"],
                "pd": data["pd"],
                "filter_flag": False,
            }

            existing = states.get(token)
            if existing is None:
                client_inserts.append(
                    {"token": token, "cohort_reference": None, **values}
                )
                previous_state = None
                tipo = ClientChangeType.NEW_CLIENT
            else:
                client_updates.append({"id": existing.id, **values})
                previous_state = {
                    "run_id": existing.last_run_id,
                    "suggested_limit": float(existing.last_suggested_limit),
                }
                tipo = ClientChangeType.LIMIT_UPDATED

            audit_rows.append(
                {
                    "token": token,
                    "change_type": tipo,
                    "previous_state": previous_state,
                    "current_state": {
                        "run_id": run_id,
                        "suggested_limit": limit,
                        "payment_capacity": data["capacity"],
                        "score": data["score"],
                        "pd": data["pd"],
                    },
                    "run_id": run_id,
                }
            )

        client_repo.bulk_write(inserts=client_inserts, updates=client_updates)
        history_repo.bulk_register_changes(audit_rows)

        # Persist clusters when the payload includes them
        result_portfolio_payload = result_payload.get("result_portfolio") or {}
        clusters = result_payload.get("clusters") or result_portfolio_payload.get("clusters") or []
        if clusters and not run_cluster_repo.get_by_run(run_id):
            for cluster in clusters:
                run_cluster_repo.create(
                    run_cluster_repo.model(
                        run_id=run_id,
                        cluster_id=cluster.get("cluster_id"),
                        total_clients=cluster.get("total_clients", 0),
                        average_pd=cluster.get("average_pd", 0),
                        average_score=cluster.get("average_score", 0),
                        average_capacity=cluster.get("average_capacity", 0),
                        policy_name=cluster.get("policy_name"),
                        leverage_multiplier=cluster.get("leverage_multiplier"),
                    )
                )

        run = run_repo.get_by_id(run_id)
        time_ms = int(result_payload.get("execution_time_ms") or 0)
        if not time_ms and run is not None:
            time_ms = _compute_run_duration_ms(run)
        run_repo.mark_success(run_id, time_ms=time_ms)

    update_run_progress(run_id, RunState.COMPLETED, finish=True)


__all__ = [
    "enqueue_run_for_processing",
    "get_status",
    "get_result",
    "is_run_already_completed",
    "update_run_status",
    "mark_run_processing",
    "update_run_progress",
    "complete_run",
    "fail_run",
]
