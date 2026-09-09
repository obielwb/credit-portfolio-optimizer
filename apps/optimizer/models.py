






from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Client:


    token: str
    product_pd: float
    payment_capacity: float
    contract_propensity_score: float
    filter_flag: bool = False


@dataclass(frozen=True)
class ModelParameters:
    """Agrupa all os parameters globais usados pelos algorithms."""

    interchange: float = 0.0175
    lgd: float = 0.80
    min_limit: float = 0.0
    max_rejected_limit: float = 200.0
    max_limit: float = 25000.0
    baseline_default_rate: float = 0.0553
    limit_step: float = 50.0
    utilization_rate: float = 0.70
    enabled: bool = True
    n_clusters: int | None = None
    max_clients_per_cluster: int = 1000
    min_clusters: int = 100
    filter: bool = True


@dataclass(frozen=True)
class ClientEvaluation:


    client: Client
    limit_candidate: float
    expected_income: float
    expected_loss: float
    expected_return: float


@dataclass(frozen=True)
class ClientResult:


    client: Client
    suggested_limit: float
    expected_income: float
    expected_loss: float
    expected_return: float


@dataclass(frozen=True)
class ClusterResult:


    cluster_id: int
    total_clients: int
    average_pd: float
    average_score: float
    average_capacity: float
    policy_name: str
    leverage_multiplier: float


@dataclass(frozen=True)
class PortfolioResult:


    clients: list[ClientResult]
    total_limit: float
    total_income: float
    total_loss: float
    total_return: float
    financial_default_rate: float
    baseline_default_rate: float
    algorithm: str = "not_provided"
    clusters: tuple[ClusterResult, ...] = ()
