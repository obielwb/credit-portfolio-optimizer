





from __future__ import annotations

import csv
import math
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from models import Client, PortfolioResult


REQUIRED_COLUMNS = {
    "token",
    "product_pd",
    "payment_capacity",
    "contract_propensity_score",
    "filter_flag",
}


def decimal_to_float(value: Any) -> float:








    if isinstance(value, str):
        return float(value.replace(",", "."))
    return float(value)


def parse_filter_flag(value: Any) -> bool:


    return int(float(value)) != 0


def count_parquet_rows(path: str | Path) -> int:


    try:
        import pyarrow.parquet as pq
    except ImportError as error:
        raise RuntimeError(
            "Counting Parquet rows requires pyarrow. Install it with: pip install -r requirements.txt"
        ) from error

    return pq.ParquetFile(Path(path)).metadata.num_rows


def load_data(
    path: str | Path,
    *,
    eligible_only: bool = False,
) -> list[dict[str, Any]]:











    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return _load_csv(path)
    if suffix in {".parquet", ".pq"}:
        return _load_parquet(path, eligible_only=eligible_only)

    raise ValueError(f"Unsupported format: '{suffix}'. Use .csv or .parquet.")


def _load_csv(path: Path) -> list[dict[str, Any]]:

    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        _validate_columns(reader.fieldnames or [])
        return list(reader)


def _load_parquet(
    path: Path,
    *,
    eligible_only: bool = False,
) -> list[dict[str, Any]]:

    try:
        import pandas as pd
    except ImportError as error:
        raise RuntimeError("Reading Parquet requires pandas and pyarrow.") from error
    try:
        import pyarrow  # noqa: F401
    except ImportError as error:
        raise RuntimeError(
            "Reading Parquet requires pyarrow. Install it with: pip install -r requirements.txt"
        ) from error

    read_kwargs: dict[str, Any] = {}
    if eligible_only:
        read_kwargs["filters"] = [("filter_flag", "=", 0)]

    df = pd.read_parquet(path, **read_kwargs)
    _validate_columns(df.columns)
    return df.to_dict("records")


def _validate_columns(columns: Iterable[str]) -> None:

    missing = REQUIRED_COLUMNS - set(columns)
    if missing:
        missing_columns = ", ".join(sorted(missing))
        raise ValueError(f"Missing columns in file: {missing_columns}")


def preprocess(rows: Iterable[Mapping[str, Any]]) -> list[Client]:









    records = [
        row
        for row in rows
        if all(_is_present(row.get(column)) for column in REQUIRED_COLUMNS)
    ]


    propensities = [
        decimal_to_float(row["contract_propensity_score"])
        for row in records
    ]
    normalized_propensities = _minmax_normalize(propensities)

    clients: list[Client] = []
    for row, propensity in zip(records, normalized_propensities):
        clients.append(
            Client(
                token=str(row["token"]),
                product_pd=decimal_to_float(row["product_pd"]),
                payment_capacity=decimal_to_float(row["payment_capacity"]),
                contract_propensity_score=propensity,
                filter_flag=parse_filter_flag(row["filter_flag"]),
            )
        )
    return clients


def _is_present(value: Any) -> bool:

    if value is None:
        return False
    if str(value).strip() == "":
        return False
    try:
        if math.isnan(float(value)):
            return False
    except (TypeError, ValueError):
        pass
    return True


def _minmax_normalize(values: list[float]) -> list[float]:

    if not values:
        return []
    minimum = min(values)
    maximum = max(values)
    if minimum == maximum:
        return [1.0] * len(values)
    return [(v - minimum) / (maximum - minimum) for v in values]


def read_clients(path: str | Path) -> list[Client]:


    return preprocess(load_data(path))


def save_result_csv(result: PortfolioResult, path: Path) -> None:
    """Write the standardized portfolio result to CSV."""

    fields = [
        "token",
        "product_pd",
        "payment_capacity",
        "normalized_propensity_score",
        "suggested_limit",
        "expected_income",
        "expected_loss",
        "expected_return",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for client in result.clients:
            writer.writerow({
                "token": client.client.token,
                "product_pd": client.client.product_pd,
                "payment_capacity": client.client.payment_capacity,
                "normalized_propensity_score": client.client.contract_propensity_score,
                "suggested_limit": client.suggested_limit,
                "expected_income": client.expected_income,
                "expected_loss": client.expected_loss,
                "expected_return": client.expected_return,
            })
