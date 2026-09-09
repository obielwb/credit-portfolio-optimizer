

from __future__ import annotations

from .models import ClusteringConfig


def build_default_clustering_config(max_clients_per_cluster: int) -> ClusteringConfig:






    return ClusteringConfig(
        enabled=True,
        max_clients_per_cluster=max_clients_per_cluster,
    )
