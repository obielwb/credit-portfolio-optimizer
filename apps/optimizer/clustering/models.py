

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ClusteringConfig:


    enabled: bool
    max_clients_per_cluster: int
    min_clusters: int = 100
    n_clusters: int | None = None
    strategy: str = "kmeans"
    feature_set: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ClusterMember:


    token: str
    product_pd: float
    payment_capacity: float
    contract_propensity_score: float
    cluster_id: int


@dataclass(frozen=True)
class ClusterMetrics:


    client_count: int
    average_pd: float
    average_score: float
    average_capacity: float
    pd_stddev: float
    score_stddev: float
    risk_score: float
    risk_level: str
    leverage_multiplier: float


@dataclass(frozen=True)
class ClusterPolicy:


    policy_name: str
    policy_version: str
    risk_band: str
    max_limit_factor: float
    leverage_table_reference: str


@dataclass(frozen=True)
class ClusterResult:
    """Final result for an individual cluster."""

    cluster_id: int
    metrics: ClusterMetrics
    policy: ClusterPolicy
    created_at: datetime
    members: tuple[ClusterMember, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ClusteringResult:


    clusters: list[ClusterResult]
    config: ClusteringConfig
    algorithm_name: str
    algorithm_version: str
    total_clients: int
    total_clusters: int

    client_cluster_ids: tuple[int, ...] = ()


__all__ = [
    "ClusterMember",
    "ClusterMetrics",
    "ClusterPolicy",
    "ClusterResult",
    "ClusteringConfig",
    "ClusteringResult",
]