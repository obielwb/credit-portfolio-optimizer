

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .models import ClusterResult, ClusteringConfig


@dataclass(frozen=True)
class PreprocessedClientInput:


    token: str
    product_pd: float
    payment_capacity: float
    contract_propensity_score: float
    filter_flag: bool = False
    extra_features: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ClusteringInput:


    clients: tuple[PreprocessedClientInput, ...]
    config: ClusteringConfig
    run_id: int | None = None
    source_file_id: int | None = None


@dataclass(frozen=True)
class SimplexClusterSummary:


    cluster_id: int
    client_count: int
    average_pd: float
    average_score: float
    average_capacity: float
    risk_level: str
    leverage_multiplier: float
    max_limit_factor: float
    policy_name: str
    policy_version: str
    client_tokens: tuple[str, ...] = ()
    filter_flag_eligible: bool = True

    @classmethod
    def from_cluster_result(cls, cluster: ClusterResult) -> "SimplexClusterSummary":


        return cls(
            cluster_id=cluster.cluster_id,
            client_count=cluster.metrics.client_count,
            average_pd=cluster.metrics.average_pd,
            average_score=cluster.metrics.average_score,
            average_capacity=cluster.metrics.average_capacity,
            risk_level=cluster.metrics.risk_level,
            leverage_multiplier=cluster.metrics.leverage_multiplier,
            max_limit_factor=cluster.policy.max_limit_factor,
            policy_name=cluster.policy.policy_name,
            policy_version=cluster.policy.policy_version,
        )


__all__ = [
    "ClusteringInput",
    "PreprocessedClientInput",
    "SimplexClusterSummary",
]