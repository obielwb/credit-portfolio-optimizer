"""Domain models for optimization parameters."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from src.custom_types import MultiplierPD, TabelaMultipliers

DEFAULT_MULTIPLIERS: TabelaMultipliers = [
    MultiplierPD(
        min_pd=Decimal("0.0000"),
        max_pd=Decimal("0.1000"),
        multiplier=Decimal("1.7000"),
    ),
    MultiplierPD(
        min_pd=Decimal("0.1000"),
        max_pd=Decimal("0.1500"),
        multiplier=Decimal("1.4000"),
    ),
    MultiplierPD(
        min_pd=Decimal("0.1500"),
        max_pd=Decimal("0.2000"),
        multiplier=Decimal("1.0000"),
    ),
    MultiplierPD(
        min_pd=Decimal("0.2000"),
        max_pd=Decimal("0.3000"),
        multiplier=Decimal("0.6000"),
    ),
    MultiplierPD(
        min_pd=Decimal("0.3000"),
        max_pd=Decimal("1.0000"),
        multiplier=Decimal("0.3000"),
    ),
]


MIN_CLUSTERS_FLOOR = 100


@dataclass(frozen=True, slots=True)
class OptimizationParameters:
    """Global parameters used for simulation and limit optimization."""

    utilization_rate: Decimal = Decimal("0.7000")
    lgd: Decimal = Decimal("0.8000")
    min_pd: Decimal = Decimal("0.0000")
    max_pd: Decimal = Decimal("1.0000")
    filter: bool = True
    max_limit: Decimal = Decimal("25000.00")
    baseline_default_rate: Decimal = Decimal("0.0553")
    min_limit: Decimal = Decimal("0.00")
    discretize: bool = True
    interchange: Decimal = Decimal("0.0175")
    max_rejected_limit: Decimal = Decimal("200.00")
    limit_step: Decimal = Decimal("50.00")
    enabled: bool = True
    n_clusters: int | None = None
    max_clients_per_cluster: int = 1000
    min_clusters: int = MIN_CLUSTERS_FLOOR
    multipliers: TabelaMultipliers = field(
        default_factory=lambda: list(DEFAULT_MULTIPLIERS)
    )


__all__ = ["MIN_CLUSTERS_FLOOR", "DEFAULT_MULTIPLIERS", "OptimizationParameters"]
