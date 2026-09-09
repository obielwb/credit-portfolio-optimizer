

from __future__ import annotations

from ..contracts import ClusteringInput


def validate_clustering_input(payload: ClusteringInput) -> None:


    if not payload.clients:
        raise ValueError("Clustering input must contain at least one client.")

    if payload.config.max_clients_per_cluster <= 0:
        raise ValueError("The maximum cluster size must be greater than zero.")

    if payload.config.n_clusters is not None and payload.config.n_clusters <= 0:
        raise ValueError("The number of clusters must be greater than zero when provided.")

    if payload.config.min_clusters <= 0:
        raise ValueError("The minimum number of clusters must be greater than zero.")

    tokens = [client.token for client in payload.clients]
    if len(tokens) != len(set(tokens)):
        raise ValueError("Client tokens must be unique within a run.")

    for client in payload.clients:
        if client.product_pd < 0:
            raise ValueError("Client PD cannot be negative.")
        if client.payment_capacity < 0:
            raise ValueError("Client payment capacity cannot be negative.")
        if client.contract_propensity_score < 0:
            raise ValueError("Client propensity score cannot be negative.")


__all__ = ["validate_clustering_input"]
