

from __future__ import annotations

import os

from models import Client, ModelParameters


def parameters_benchmark() -> ModelParameters:


    return ModelParameters(
        min_limit=0.0,
        max_rejected_limit=200.0,
        enabled=True,
        n_clusters=None,
        max_clients_per_cluster=int(os.getenv("PERF_MAX_CLIENTS_PER_CLUSTER", "10000")),
        min_clusters=int(os.getenv("PERF_MIN_CLUSTERS", "100")),
        filter=True,
    )


def generate_benchmark_clients(n: int, *, seed: int = 42) -> list[Client]:








    clients: list[Client] = []
    for i in range(n):
        bucket = (i + seed) % 4
        if bucket == 0:
            pd = 0.35 + (i % 15) * 0.02
            cap = 250.0 + (i % 8) * 50.0
            score = 0.02 + (i % 5) * 0.01
        elif bucket == 1:
            pd = 0.18 + (i % 10) * 0.01
            cap = 800.0 + (i % 20) * 80.0
            score = 0.08 + (i % 8) * 0.02
        elif bucket == 2:
            pd = 0.08 + (i % 8) * 0.005
            cap = 1500.0 + (i % 30) * 120.0
            score = 0.15 + (i % 6) * 0.03
        else:
            pd = 0.12 + (i % 12) * 0.008
            cap = 600.0 + (i % 15) * 200.0
            score = 0.25 + (i % 10) * 0.04

        clients.append(
            Client(
                token=str(i),
                product_pd=min(pd, 0.95),
                payment_capacity=cap,
                contract_propensity_score=min(score, 1.0),
            )
        )
    return clients


def expected_minimum_clusters(n_clients: int, parameters: ModelParameters) -> int:


    if not parameters.enabled:
        return 0
    return min(max(1, parameters.min_clusters), n_clients)


def validate_active_clustering(result, parameters: ModelParameters, n_clients: int) -> None:


    if not parameters.enabled:
        raise AssertionError("Benchmark exige parameters.enabled=True")
    minimum = expected_minimum_clusters(n_clients, parameters)
    total = len(result.clusters)
    if total < minimum:
        raise AssertionError(
            f"Clustering is disabled or incomplete: expected >= {minimum} clusters, "
            f"obtido {total} (n={n_clients})"
        )


__all__ = [
    "expected_minimum_clusters",
    "generate_benchmark_clients",
    "parameters_benchmark",
    "validate_active_clustering",
]
