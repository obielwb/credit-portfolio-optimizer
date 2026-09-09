







from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.models.run import ETAPA_LABELS, RunState
from src.repositories import ClientRepository, RunRepository, RunClusterRepository
from src.services.parameters_service import _orm_to_dict
from src.services.cohort_analytics import build_return_by_cohort_legacy
from src.utils.db.session import get_db_session
from src.utils.minio import get_presigned_download_url
from src.utils.pdf_report import build_text_pdf


# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------


def get_dashboard(
    csv_file_id: int | None = None,
    run_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_order: str | None = None,
) -> dict[str, Any]:






    with get_db_session() as session:
        run_repo = RunRepository(session)
        client_repo = ClientRepository(session)

        # Resolve a run from run_id or the file's most recent run
        run = _resolve_run(run_repo, run_id, csv_file_id)
        if not run:
            return _empty_dashboard(
                csv_file_id=csv_file_id,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_order=sort_order,
            )

        file = run.file_csv
        result = run.result

        # Run clients
        clients_orm = client_repo.get_by_run(run.id)
        total_clients_run = len(clients_orm)


        total_pages = max(1, -(-total_clients_run // page_size))  # ceil division
        start = (page - 1) * page_size
        clients_page = clients_orm[start : start + page_size]

        clients_dto = [
            {
                "token": c.token,
                "payment_capacity": float(c.payment_capacity),
                "score": float(c.score),
                "suggested_limit": float(c.last_suggested_limit),
                "pd": float(c.pd),
            }
            for c in clients_page
        ]





        totais = {
            "total_clients": total_clients_run,
            "total_suggested_limit": (
                float(result.total_limit) if result else 0.0
            ),
            "approval_rate": float(_calc_approval_rate(clients_orm)),
            "expected_return": float(result.total_return) if result else 0.0,
        }

        return {
            "file": {
                "csv_file_id": file.id,
                "file_name": file.name,
                "created_at": file.created_at,
                "run_id": run.id,
            },
            "clients": clients_dto,
            "totais": totais,
            "pagina": page,
            "page_size": page_size,
            "total_items": total_clients_run,
            "total_pages": total_pages,
            "sort_by": sort_by,
            "sort_order": sort_order,
        }


def _empty_dashboard(
    *,
    csv_file_id: int | None,
    page: int,
    page_size: int,
    sort_by: str | None,
    sort_order: str | None,
) -> dict[str, Any]:

    return {
        "file": {
            "csv_file_id": csv_file_id or 0,
            "file_name": "",
            "created_at": None,
            "run_id": None,
        },
        "clients": [],
        "totais": {
            "total_clients": 0,
            "total_suggested_limit": 0.0,
            "approval_rate": 0.0,
            "expected_return": 0.0,
        },
        "pagina": page,
        "page_size": page_size,
        "total_items": 0,
        "total_pages": 1,
        "sort_by": sort_by,
        "sort_order": sort_order,
    }


def get_runs_summary() -> dict[str, Any]:

    with get_db_session() as session:
        run_repo = RunRepository(session)
        runs = run_repo.get_all()

        total = len(runs)
        completed = sum(1 for r in runs if r.status == "success")
        failed = sum(1 for r in runs if r.status in {"error", "timeout"})
        timings = [r.execution_time_ms for r in runs if r.execution_time_ms]
        avg_ms = int(sum(timings) / len(timings)) if timings else 0

        return {
            "total_runs": total,
            "completed_runs": completed,
            "failed_runs": failed,
            "avg_duration_ms": avg_ms,
        }


def get_portfolio(csv_file_id: int | None = None) -> dict[str, Any]:

    with get_db_session() as session:
        run_repo = RunRepository(session)
        client_repo = ClientRepository(session)
        result = _resolve_result(run_repo, csv_file_id)

        if not result:
            raise ValueError("No result was found.")

        portfolio = {
            "total_limit": float(result.total_limit),
            "total_income": float(result.total_income),
            "total_loss": float(result.total_loss),
            "total_return": float(result.total_return),
            "financial_default_rate": float(result.financial_default_rate),
            "baseline_default_rate": float(
                result.baseline_default_rate
            ),
            "total_clients": result.total_clients,
            "approval_rate": float(
                _calc_approval_rate(client_repo.get_by_run(result.run_id))
            ),
        }

        clients_run = client_repo.get_by_run(result.run_id)
        ranges = get_limits_buckets_from_clients(clients_run)
        clusters = RunClusterRepository(session).get_by_run(result.run_id)
        return_cohort = build_return_by_cohort_legacy(
            clusters,
            clients_run,
            float(result.total_return),
        )

        return {
            "portfolio": portfolio,
            "limit_ranges": ranges,
            "return_by_cohort": return_cohort,
        }


def get_results_by_client(
    csv_file_id: int | None = None,
    run_id: int | None = None,
    token: str | None = None,
) -> dict[str, Any]:

    with get_db_session() as session:
        run_repo = RunRepository(session)
        client_repo = ClientRepository(session)
        run = _resolve_run(run_repo, run_id, csv_file_id)
        if not run:
            raise ValueError("No run was found.")

        file = run.file_csv
        clients = client_repo.get_by_run(run.id)
        if token:
            clients = [c for c in clients if c.token == token]

        items = [
            {
                "token": c.token,
                "payment_capacity": float(c.payment_capacity),
                "propensity_score": float(c.score),
                "pd": float(c.pd),
                "suggested_limit": float(c.last_suggested_limit),


                "expected_income": 0.0,
                "expected_loss": 0.0,
                "expected_return": 0.0,
            }
            for c in clients
        ]

        return {
            "file": {
                "csv_file_id": file.id,
                "file_name": file.name,
                "created_at": file.created_at,
                "run_id": run.id,
            },
            "items": items,
            "total_items": len(items),
        }


def get_limits_buckets(csv_file_id: int | None = None) -> list[dict[str, Any]]:

    with get_db_session() as session:
        run_repo = RunRepository(session)
        client_repo = ClientRepository(session)
        run = _resolve_run(run_repo, None, csv_file_id)
        if not run:
            return []
        clients = client_repo.get_by_run(run.id)
        return get_limits_buckets_from_clients(clients)


def get_return_by_month(
    csv_file_id: int | None = None,
    run_id: int | None = None,
) -> list[dict[str, Any]]:


    with get_db_session() as session:
        run_repo = RunRepository(session)
        client_repo = ClientRepository(session)
        cluster_repo = RunClusterRepository(session)
        run = _resolve_run(run_repo, run_id, csv_file_id)
        if not run or not run.result:
            return []

        clients = client_repo.get_by_run(run.id)
        clusters = cluster_repo.get_by_run(run.id)
        return build_return_by_cohort_legacy(
            clusters,
            clients,
            float(run.result.total_return),
        )


def get_execution_history(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
) -> dict[str, Any]:


    with get_db_session() as session:
        run_repo = RunRepository(session)
        client_repo = ClientRepository(session)
        runs = run_repo.get_all()
        if status:
            runs = [run for run in runs if run.status == status]

        runs_sorted = sorted(runs, key=lambda run: run.created_at, reverse=True)

        total_items = len(runs_sorted)
        start = (page - 1) * page_size
        page_runs = runs_sorted[start : start + page_size]
        clients_by_run = _clients_by_run_batch(client_repo, [run.id for run in page_runs])

        items = []
        for run in page_runs:
            clients = clients_by_run.get(run.id, [])
            stored_approved = getattr(run.result, "approved", None) if run.result else None
            approved = (
                stored_approved if stored_approved is not None
                else (_count_approved(clients) if clients else None)
            )
            item = {
                "run_id": run.id,
                "algorithm": run.algorithm,
                "status": run.status,
                "csv_file_id": run.csv_file_id,
                "file_name": run.file_csv.name if run.file_csv else "",
                "total_clients": run.result.total_clients if run.result else len(clients),
                "created_at": run.created_at,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "execution_time_ms": _resolve_execution_time_ms(run),
                "approved": approved,
                "error_reason": run.error_reason,
                "total_limit": None,
                "approval_rate": None,
                "total_return": None,
            }
            if run.status == "success" and run.result is not None:
                item["total_limit"] = float(run.result.total_limit)
                item["total_return"] = float(run.result.total_return)
                stored_rate = getattr(run.result, "approval_rate", None)
                item["approval_rate"] = (
                    float(stored_rate) if stored_rate is not None
                    else float(_calc_approval_rate(clients))
                )
            items.append(item)

        return {"items": items, "total_items": total_items}


def get_execution_detail(run_id: int) -> dict[str, Any]:


    with get_db_session() as session:
        run_repo = RunRepository(session)
        client_repo = ClientRepository(session)
        run = run_repo.get_by_id(run_id)
        if run is None:
            raise ValueError(f"Run {run_id} not found")

        clients = client_repo.get_by_run(run_id)
        stored_approved = getattr(run.result, "approved", None) if run.result else None
        approved = stored_approved if stored_approved is not None else _count_approved(clients)
        file = run.file_csv

        detail: dict[str, Any] = {
            "run_id": run.id,
            "algorithm": run.algorithm,
            "status": run.status,
            "csv_file_id": run.csv_file_id,
            "file_name": file.name if file is not None else "",
            "created_at": run.created_at,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "execution_time_ms": _resolve_execution_time_ms(run),
            "total_clients": run.result.total_clients if run.result else len(clients),
            "approved": approved,
            "error_reason": run.error_reason,
            "parameters": _orm_to_dict(run.parameters) if run.parameters else None,
            "distribution": _calc_limit_distribution(clients) if clients else None,
            "limit_ranges": get_limits_buckets_from_clients(clients) if clients else [],
            "operational_log": _build_operational_log(run, len(clients), approved),
            "download_csv_url": _build_download_csv_url(run_id),
            "approval_rate": None,
            "average_approved_score": None,
            "total_limit": None,
            "total_return": None,
        }

        if run.result is not None:
            detail["total_limit"] = float(run.result.total_limit)
            detail["total_return"] = float(run.result.total_return)
            stored_rate = getattr(run.result, "approval_rate", None)
            if stored_rate is not None:
                detail["approval_rate"] = float(stored_rate)
            elif clients:
                detail["approval_rate"] = float(_calc_approval_rate(clients))

        if clients:
            detail["average_approved_score"] = _calc_average_approved_score(clients)

        return detail


def delete_execution(run_id: int) -> None:







    from src.schema.database import (
        Client,
        ClientHistory,
        PortfolioResults,
        Run,
        RunClusters,
    )

    with get_db_session() as session:
        run = session.get(Run, run_id)
        if run is None:
            raise ValueError(f"Run {run_id} not found")

        session.query(ClientHistory).filter(
            ClientHistory.run_id == run_id
        ).delete(synchronize_session=False)
        session.query(RunClusters).filter(
            RunClusters.run_id == run_id
        ).delete(synchronize_session=False)
        session.query(PortfolioResults).filter(
            PortfolioResults.run_id == run_id
        ).delete(synchronize_session=False)
        session.query(Client).filter(
            Client.last_run_id == run_id
        ).delete(synchronize_session=False)
        session.delete(run)


def generate_report_pdf(
    csv_file_id: int | None = None,
    run_id: int | None = None,
) -> tuple[bytes, str]:


    with get_db_session() as session:
        run_repo = RunRepository(session)
        run = _resolve_run(run_repo, run_id, csv_file_id)
        if not run:
            raise ValueError("No run was found for report generation.")

        file = run.file_csv
        lines = [
            "Execution report — Credit Limit Optimizer",
            f"Run ID: {run.id}",
            f"File: {file.name if file else '—'}",
            f"Algorithm: {run.algorithm}",
            f"Status: {run.status}",
            f"Created em: {run.created_at}",
        ]

        if run.result is not None:
            result = run.result
            lines.extend(
                [
                    "",
                    "Portfolio metrics",
                    f"Total clients: {result.total_clients}",
                    f"Limit total sugerido: {float(result.total_limit):,.2f}",
                    f"Return total: {float(result.total_return):,.2f}",
                    f"Loss total: {float(result.total_loss):,.2f}",
                    f"DefaultRate financeira: {float(result.financial_default_rate):.4f}",
                ]
            )
            clients = ClientRepository(session).get_by_run(run.id)
            if clients:
                lines.append(f"Approval rate: {float(_calc_approval_rate(clients)):.2%}")
                ranges = get_limits_buckets_from_clients(clients)
                lines.append("")
                lines.append("Distribution by limit range")
                for range in ranges:
                    lines.append(
                        f"- {range['range']}: {range['count']} clients "
                        f"({range['percentage']}%)"
                    )
        elif run.error_reason:
            lines.extend(["", f"Error: {run.error_reason}"])

        filename = f"report-run-{run.id}.pdf"
        return build_text_pdf(lines), filename


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _resolve_run(
    run_repo: RunRepository,
    run_id: int | None,
    csv_file_id: int | None,
) -> Any | None:

    if run_id is not None:
        return run_repo.get_by_id(run_id)
    if csv_file_id is not None:
        return run_repo.get_latest_by_file(csv_file_id)

    runs = run_repo.get_all()
    return max(runs, key=lambda r: r.id) if runs else None


def _resolve_result(
    run_repo: RunRepository,
    csv_file_id: int | None,
) -> Any | None:

    run = _resolve_run(run_repo, None, csv_file_id)
    return run.result if run else None


def _resolve_execution_time_ms(run: Any) -> int:


    if run.execution_time_ms:
        return int(run.execution_time_ms)
    start = run.started_at or run.created_at
    end = run.finished_at
    if start and end:
        elapsed = (end - start).total_seconds()
        return max(0, int(elapsed * 1000))
    return 0


def _count_approved(clients: list) -> int:

    return sum(1 for client in clients if client.last_suggested_limit > 0)


def _calc_average_approved_score(clients: list) -> float:

    approved = [c for c in clients if c.last_suggested_limit > 0]
    if not approved:
        return 0.0
    return float(sum(float(c.score) for c in approved) / len(approved))


def _calc_limit_distribution(clients: list) -> dict[str, int]:
    """Classify suggested limits versus payment capacity."""

    above = 0
    full = 0
    denied = 0
    for client in clients:
        limit = float(client.last_suggested_limit)
        capacity = float(client.payment_capacity)
        if limit <= 0:
            denied += 1
        elif limit > capacity:
            above += 1
        else:
            full += 1
    return {"above": above, "full": full, "denied": denied}


def _format_log_time(value: Any) -> str:

    if value is None:
        return "—"
    return value.strftime("%H:%M:%S")


def _build_operational_log(run: Any, total_clients: int, approved: int) -> list[dict[str, str]]:
    """Build a synthetic log from the run's final state."""

    entries: list[dict[str, str]] = [
        {
            "t": _format_log_time(run.created_at),
            "tipo": "info",
            "msg": f"Job registrado — run #{run.id}",
        }
    ]

    if run.started_at:
        entries.append(
            {
                "t": _format_log_time(run.started_at),
                "tipo": "info",
                "msg": "Processamento started",
            }
        )

    if total_clients:
        entries.append(
            {
                "t": _format_log_time(run.started_at or run.created_at),
                "tipo": "ok",
                "msg": f"Data loaded — {total_clients} clients in the batch",
            }
        )

    if run.parameters is not None:
        entries.append(
            {
                "t": _format_log_time(run.started_at or run.created_at),
                "tipo": "info",
                "msg": f"Parameters v{run.parameters.id} applied",
            }
        )

    if run.state_operacional:
        try:
            state = RunState(run.state_operacional)
            label = ETAPA_LABELS.get(state, run.state_operacional)
        except ValueError:
            label = run.state_operacional
        if run.status not in {"error", "timeout"} and state not in {
            RunState.COMPLETED,
            RunState.FAILED,
        }:
            entries.append(
                {
                    "t": _format_log_time(run.finished_at or run.started_at),
                    "tipo": "info",
                    "msg": label,
                }
            )

    end_time = run.finished_at or run.created_at
    if run.status == "success":
        entries.append(
            {
                "t": _format_log_time(end_time),
                "tipo": "ok",
                "msg": f"Job completed — {approved} suggested limits",
            }
        )
    elif run.status in {"error", "timeout"}:
        entries.append(
            {
                "t": _format_log_time(end_time),
                "tipo": "error",
                "msg": run.error_reason or "Execution failed",
            }
        )

    return entries


def _build_download_csv_url(run_id: int) -> str:

    return f"/results/executions/{run_id}/download"


def _calc_approval_rate(clients: list) -> Decimal:

    if not clients:
        return Decimal("0")
    approved = sum(1 for c in clients if c.last_suggested_limit > 0)
    return Decimal(approved) / Decimal(len(clients))


def _clients_by_run_batch(
    client_repo: ClientRepository,
    run_ids: list[int],
) -> dict[int, list]:


    if not run_ids:
        return {}

    grouped: dict[int, list] = {run_id: [] for run_id in run_ids}
    Client = client_repo.model
    clients = (
        client_repo.session.query(Client)
        .filter(Client.last_run_id.in_(run_ids))
        .all()
    )
    for client in clients:
        grouped.setdefault(client.last_run_id, []).append(client)
    return grouped


def get_limits_buckets_from_clients(clients: list) -> list[dict[str, Any]]:

    ranges = [
        ("0-1k", 0, 1000),
        ("1k-5k", 1000, 5000),
        ("5k-10k", 5000, 10000),
        ("10k-15k", 10000, 15000),
        ("15k-20k", 15000, 20000),
        ("20k-25k", 20000, 25000),
    ]
    totais = {name: 0 for name, _, _ in ranges}
    total = len(clients)

    for c in clients:
        limit = float(c.last_suggested_limit)
        for name, lower, upper in ranges:
            if lower <= limit < upper or (name == "20k-25k" and limit == upper):
                totais[name] += 1
                break

    return [
        {
            "range": name,
            "count": qtd,
            "percentage": round(qtd / total * 100, 2) if total else 0.0,
        }
        for name, qtd in totais.items()
    ]


def get_return_by_month_from_db(
    run_id: int | None = None,
    *,
    csv_file_id: int | None = None,
) -> list[dict[str, Any]]:


    return get_return_by_month(csv_file_id=csv_file_id, run_id=run_id)


def resolve_csv_download(run_id: int) -> tuple[str, str]:


    with get_db_session() as session:
        run_repo = RunRepository(session)
        run = run_repo.get_by_id(run_id)
        if run is None or run.file_csv is None:
            raise ValueError(f"Run {run_id} or file not found")
        file = run.file_csv
        url = get_presigned_download_url(file.path_or_url)
        return url, file.name


def _limits_sugeridos_by_run(session, run_id: int) -> dict[str, float]:







    from src.repositories import ClientHistoryRepository

    history = ClientHistoryRepository(session).find_by(run_id=run_id)
    limits: dict[str, float] = {}
    for record in history:
        state = record.current_state or {}
        if "suggested_limit" in state:
            limits[record.token] = float(state["suggested_limit"])

    if not limits:
        for client in ClientRepository(session).get_by_run(run_id):
            limits[client.token] = float(client.last_suggested_limit)

    return limits


def build_run_result_csv(run_id: int) -> tuple[bytes, str]:






    import io

    import pandas as pd

    from src.utils.minio import get_object_bytes

    with get_db_session() as session:
        run_repo = RunRepository(session)
        run = run_repo.get_by_id(run_id)
        if run is None or run.file_csv is None:
            raise ValueError(f"Run {run_id} or file not found")
        path_or_url = run.file_csv.path_or_url
        name = run.file_csv.name
        limits = _limits_sugeridos_by_run(session, run_id)

    content, _ = get_object_bytes(path_or_url)
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext in {"parquet", "pq"}:
        df = pd.read_parquet(io.BytesIO(content))
    else:
        df = pd.read_csv(io.BytesIO(content))

    if "token" not in df.columns:
        raise ValueError(
            "The input file has no 'token' column; it is not possible to "
            "associate algorithm limits."
        )

    df["suggested_limit"] = df["token"].astype(str).map(limits)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    base = name.rsplit(".", 1)[0] if "." in name else name
    filename = f"result_{base}.csv"
    return csv_bytes, filename


__all__ = [
    "get_dashboard",
    "get_runs_summary",
    "get_portfolio",
    "get_results_by_client",
    "get_limits_buckets",
    "get_return_by_month",
    "get_execution_history",
    "get_execution_detail",
    "generate_report_pdf",
    "resolve_csv_download",
    "build_run_result_csv",
]
