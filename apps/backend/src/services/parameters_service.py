

from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.models.parameters import MIN_CLUSTERS_FLOOR
from src.schema.database.parameters import Parameters as ParametersORM
from src.repositories import ParametersRepository
from src.utils.db.session import get_db_session


# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------


def get_active() -> dict[str, Any] | None:





    with get_db_session() as session:
        params_repo = ParametersRepository(session)
        latest = params_repo.get_latest()
        if not latest:
            return None
        return _orm_to_dict(latest)


def update_active(data: dict[str, Any]) -> dict[str, Any]:










    _validate(data)

    with get_db_session() as session:
        params_repo = ParametersRepository(session)
        orm = ParametersORM(
            utilization_rate=Decimal(str(data["utilization_rate"])),
            lgd=Decimal(str(data["lgd"])),
            min_pd=Decimal(str(data["min_pd"])),
            max_pd=Decimal(str(data["max_pd"])),
            filter=bool(data["filter"]),
            max_limit=Decimal(str(data["max_limit"])),
            baseline_default_rate=Decimal(
                str(data["baseline_default_rate"])
            ),
            min_limit=Decimal(str(data["min_limit"])),
            discretize=bool(data["discretize"]),
            interchange=Decimal(str(data["interchange"])),
            max_rejected_limit=Decimal(str(data["max_rejected_limit"])),
            enabled=bool(data["enabled"]),
            n_clusters=int(data["n_clusters"]) if data.get("n_clusters") is not None else None,
            max_clients_per_cluster=int(data["max_clients_per_cluster"]),
            min_clusters=int(data.get("min_clusters", MIN_CLUSTERS_FLOOR)),
            multipliers=data["multipliers"],
        )
        created = params_repo.create(orm)
        return _orm_to_dict(created)


def list_versions() -> list[dict[str, Any]]:

    with get_db_session() as session:
        params_repo = ParametersRepository(session)
        all_params = params_repo.get_all()
        return [
            _orm_to_dict(p)
            for p in sorted(all_params, key=lambda p: p.id, reverse=True)
        ]


def _orm_to_dict(orm: ParametersORM) -> dict[str, Any]:

    return {
        "id": orm.id,
        "utilization_rate": float(orm.utilization_rate),
        "lgd": float(orm.lgd),
        "min_pd": float(orm.min_pd),
        "max_pd": float(orm.max_pd),
        "filter": orm.filter,
        "max_limit": float(orm.max_limit),
        "baseline_default_rate": float(
            orm.baseline_default_rate
        ),
        "min_limit": float(orm.min_limit),
        "discretize": orm.discretize,
        "interchange": float(orm.interchange),
        "max_rejected_limit": float(orm.max_rejected_limit),
        "enabled": orm.enabled,
        "n_clusters": orm.n_clusters,
        "max_clients_per_cluster": orm.max_clients_per_cluster,
        "min_clusters": orm.min_clusters,
        "multipliers": orm.multipliers,
        "created_at": orm.created_at,
    }


def _validate(data: dict[str, Any]) -> None:


    def _dec(k: str) -> Decimal:

        return Decimal(str(data[k]))

    if "baseline_default_rate" in data:
        v = _dec("baseline_default_rate")
        if not (Decimal("0") < v < Decimal("1")):
            raise ValueError(
                f"baseline_default_rate must be between 0 and 1; received: {v}"
            )

    if "min_pd" in data and "max_pd" in data:
        if _dec("min_pd") >= _dec("max_pd"):
            raise ValueError("min_pd must be lower than max_pd.")

    if "utilization_rate" in data:
        v = _dec("utilization_rate")
        if not (Decimal("0") < v <= Decimal("1")):
            raise ValueError(f"utilization_rate must be between 0 and 1; received: {v}")

    if "lgd" in data:
        v = _dec("lgd")
        if not (Decimal("0") < v <= Decimal("1")):
            raise ValueError(f"lgd must be between 0 and 1; received: {v}")

    if "max_rejected_limit" in data:
        v = _dec("max_rejected_limit")
        if v < Decimal("200"):
            raise ValueError(
                f"max_rejected_limit cannot be lower than R$200, received: {v}"
            )

    if "max_clients_per_cluster" in data:
        v = int(data["max_clients_per_cluster"])
        if v <= 0:
            raise ValueError(
                f"max_clients_per_cluster must be greater than zero, received: {v}"
            )

    if "n_clusters" in data and data.get("n_clusters") is not None:
        v = int(data["n_clusters"])
        if v <= 0:
            raise ValueError(f"n_clusters must be greater than zero, received: {v}")

    if "min_clusters" in data:
        v = int(data["min_clusters"])
        if v < MIN_CLUSTERS_FLOOR:
            raise ValueError(
                f"min_clusters must be at least {MIN_CLUSTERS_FLOOR}, received: {v}"
            )


__all__ = ["get_active", "update_active", "list_versions"]
