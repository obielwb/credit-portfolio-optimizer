"""Build algorithm input from clients persisted in the database."""

from __future__ import annotations

from typing import Any

from src.repositories import ClientRepository
from src.schema import OptimizationJobSchema
from src.schema.database.client import Client as ClientORM
from src.utils.algorithm_path import ensure_algorithm_path
from src.utils.db.session import get_db_session


def load_clients_for_job(job: OptimizationJobSchema) -> list[Any]:






    ensure_algorithm_path()
    from ingestion import preprocess  # type: ignore import-not-found

    clients_db = _fetch_clients(job)
    if not clients_db:
        raise ValueError(
            f"No persisted client was found for run_id={job.run_id}."
        )

    rows = [_client_to_pipeline_row(client) for client in clients_db]
    clients = preprocess(rows)
    if not clients:
        raise ValueError(
            f"No valid client remained after preprocessing for run_id={job.run_id}. "
            f"Persistidos no database: {len(clients_db)}."
        )
    return clients


def _fetch_clients(job: OptimizationJobSchema) -> list[ClientORM]:

    with get_db_session() as session:
        client_repo = ClientRepository(session)
        clients_db = client_repo.get_by_run(job.run_id)

    if not job.client_tokens:
        return clients_db

    by_token = {client.token: client for client in clients_db}
    return [by_token[token] for token in job.client_tokens if token in by_token]


def _client_to_pipeline_row(client: ClientORM) -> dict[str, Any]:

    return {
        "token": client.token,
        "product_pd": float(client.pd),
        "payment_capacity": float(client.payment_capacity),
        "contract_propensity_score": float(client.score),
        "filter_flag": int(client.filter_flag),
    }


__all__ = ["load_clients_for_job"]
