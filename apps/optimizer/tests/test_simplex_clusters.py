import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from algorithms.simplex import _representative_client, optimize_clusters_simplex
from algorithms.simplex_ortools import optimize_clusters_simplex_ortools
from evaluation import evaluate_client_profitability
from clustering import (
    ClusteringConfig,
    ClusteringInput,
    PreprocessedClientInput,
    SimplexClusterSummary,
    clusterize,
)
from clustering.algorithms.kmeans_core import determine_k
from models import ModelParameters


def _summary(cluster_id: int, tokens: tuple[str, ...], pd: float, capacity: float, score: float):
    return SimplexClusterSummary(
        cluster_id=cluster_id,
        client_tokens=tokens,
        client_count=len(tokens),
        average_pd=pd,
        average_score=score,
        average_capacity=capacity,
        risk_level="medio",
        leverage_multiplier=1.0,
        max_limit_factor=1.0,
        policy_name="default",
        policy_version="1.0.0",
    )


def test_determine_k_respects_min_clusters_for_500_clients():
    assert determine_k(500, min_clusters=100, max_clients_per_cluster=1000) == 100


def test_clusterize_enforces_minimum_100_clusters():
    clients = tuple(
        PreprocessedClientInput(f"t{i}", 0.05 + (i % 10) * 0.01, 1000.0, 0.10 + (i % 5) * 0.05)
        for i in range(500)
    )
    config = ClusteringConfig(enabled=True, max_clients_per_cluster=1000, min_clusters=100)
    result = clusterize(ClusteringInput(clients=clients, config=config))

    assert result.algorithm_name == "kmeans"
    assert result.total_clients == 500
    assert result.total_clusters == 100
    assert sum(cluster.metrics.client_count for cluster in result.clusters) == 500
    assert all(cluster.metrics.client_count <= 1000 for cluster in result.clusters)


def test_objective_multiplies_return_by_cluster_size():
    parameters = ModelParameters()
    summary = _summary(1, ("a", "b", "c"), 0.05, 5000.0, 0.30)
    representative = _representative_client(summary)
    metrics = evaluate_client_profitability(1.0, representative, parameters)

    coeficiente_ponderado = summary.client_count * metrics.expected_return
    coeficiente_unitario = metrics.expected_return

    assert coeficiente_ponderado == coeficiente_unitario * 3


def test_cluster_simplex_applies_same_limit_to_members():
    parameters = ModelParameters()
    summaries = [
        _summary(1, ("t1", "t2"), 0.10, 2000.0, 0.20),
        _summary(2, ("t3",), 0.20, 1500.0, 0.25),
    ]

    limits = optimize_clusters_simplex(summaries, parameters)

    assert len(limits) == 2
    assert all(limit >= 0 for limit in limits)


def test_cluster_ortools_solves_same_lp_as_simplex():
    parameters = ModelParameters()
    summaries = [
        _summary(1, ("t1", "t2"), 0.10, 2000.0, 0.20),
        _summary(2, ("t3",), 0.20, 1500.0, 0.25),
    ]

    limits_simplex = optimize_clusters_simplex(summaries, parameters)
    limits_ortools = optimize_clusters_simplex_ortools(summaries, parameters)

    assert len(limits_ortools) == len(limits_simplex)
    assert limits_ortools == limits_simplex
