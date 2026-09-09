
















from __future__ import annotations

import io
from decimal import Decimal
from typing import Any

import pandas as pd

from src.schema.database.csv_file import CsvFile as CsvFileORM
from src.schema.database.run import Run as RunORM
from src.models.client import OptimizationClient
from src.models.run import RunStatus
from src.repositories import (
    CsvFileRepository,
    ClientRepository,
    ParametersRepository,
    RunRepository,
)
from src.services.optimization_service import (
    enqueue_run_for_processing,
    fail_run,
    update_run_progress,
)
from src.models.run import RunState
from src.utils.db.session import get_db_session
from src.utils import upload_csv_to_minio
from src.utils.algorithm import normalize_algorithm

DEFAULT_ALGORITHM = "simplex"

INTERNAL_COLUMNS: set[str] = {
    "token",
    "product_pd",
    "payment_capacity",
    "contract_propensity_score",
    "filter_flag",
}

# Nomes da base do parceiro → names internos do optimizer
PARTNER_COLUMN_ALIASES: dict[str, str] = {
    "default_probability": "product_pd",
    "contract_propensity": "contract_propensity_score",
}

REQUIRED_COLUMNS = INTERNAL_COLUMNS

NON_NULLABLE_COLUMNS = INTERNAL_COLUMNS


# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------


async def start_ingestion(
    contents: bytes,
    filename: str,
    file_ref: str | None = None,
    *,
    algorithm: str = DEFAULT_ALGORITHM,
) -> dict[str, Any]:












    algorithm = normalize_algorithm(algorithm)


    df = _parse_bytes(contents, filename)
    df = _normalize_partner_columns(df)
    _validate_or_raise(df)
    df_clean = _clean(df)
    clients = to_optimization_clients(df_clean)
    total_eligible = len(clients)
    client_tokens = [client.token for client in clients]

    del df, df_clean

    path_or_url = upload_csv_to_minio(contents, filename, file_ref)

    run_id: int | None = None
    file_id: int | None = None
    params_id: int | None = None

    with get_db_session() as session:
        file_repo = CsvFileRepository(session)
        params_repo = ParametersRepository(session)
        run_repo = RunRepository(session)

        params = params_repo.get_latest()
        if not params:
            raise ValueError(
                "No parameter set was found. "
                "Configure the parameters before starting ingestion."
            )
        params_id = params.id

        file = CsvFileORM(name=filename, path_or_url=path_or_url)
        file = file_repo.create(file)
        file_id = file.id

        run = RunORM(
            algorithm=algorithm,
            execution_time_ms=0,
            status=RunStatus.PENDING.value,
            parameters_id=params.id,
            csv_file_id=file.id,
        )
        run = run_repo.create(run)
        run_id = run.id

    update_run_progress(run_id, RunState.INGESTION, start=True)

    try:
        with get_db_session() as session:
            ClientRepository(session).bulk_upsert_from_ingestion(clients, run_id)
    except Exception as exc:
        fail_run(run_id, str(exc), stage="ingestion")
        raise

    try:
        queue_result = await enqueue_run_for_processing(
            run_id=run_id,
            algorithm=algorithm,
            parameters_id=params_id,
            client_tokens=client_tokens,
        )
    except Exception:
        raise

    update_run_progress(run_id, RunState.WAITING_FOR_PROCESSING)

    return {
        "run_id": run_id,
        "csv_file_id": file_id,
        "filename": filename,
        "algorithm": algorithm,
        "state": "queued",
        "total_clients": total_eligible,
        "client_tokens": client_tokens,
        "queue": queue_result["queue"],
    }


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _parse_bytes(contents: bytes, filename: str) -> pd.DataFrame:

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in {"parquet", "pq"}:
        return pd.read_parquet(io.BytesIO(contents))
    if ext == "csv":
        return pd.read_csv(io.BytesIO(contents))
    raise ValueError(f"Unsupported format: '{ext}'. Use .csv or .parquet.")


def _normalize_partner_columns(df: pd.DataFrame) -> pd.DataFrame:

    rename_map = {
        partner: internal
        for partner, internal in PARTNER_COLUMN_ALIASES.items()
        if partner in df.columns and internal not in df.columns
    }
    if not rename_map:
        return df
    return df.rename(columns=rename_map)


def _validate_or_raise(df: pd.DataFrame) -> None:

    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """Remove invalid rows and fill missing DataFrame values."""
    before = len(df)
    df = df.dropna(subset=list(NON_NULLABLE_COLUMNS))

    numeric_cols = df.select_dtypes(include="number").columns
    df[numeric_cols] = df[numeric_cols].fillna(0)
    categorical_cols = df.select_dtypes(include="object").columns
    df[categorical_cols] = df[categorical_cols].fillna("unknown")
    removed = before - len(df)
    if removed:
        print(f"[IngestionService] {removed} rows removed during cleaning.")
    return df.reset_index(drop=True)


def to_optimization_clients(df: pd.DataFrame) -> list[OptimizationClient]:


    has_cohort = "cohort_reference" in df.columns
    clients: list[OptimizationClient] = []
    for row in df.itertuples(index=False):
        cohort_reference = str(row.cohort_reference) if has_cohort and row.cohort_reference else None
        clients.append(
            OptimizationClient(
                token=str(row.token),
                pd=Decimal(str(row.product_pd)),
                payment_capacity=Decimal(str(row.payment_capacity)),
                propensity_score=Decimal(str(row.contract_propensity_score)),
                filter_flag=bool(int(float(row.filter_flag))),
                cohort_reference=cohort_reference,
            )
        )
    return clients


__all__ = ["start_ingestion", "to_optimization_clients"]
