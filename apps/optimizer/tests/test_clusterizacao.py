import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from clustering import (
    ClusteringConfig,
    ClusteringInput,
    PreprocessedClientInput,
    clusterize,
    summarize_for_simplex,
)
from clustering.algorithms.kmeans_core import determine_k


def test_clusterize_groups_clients_with_kmeans():
    config = ClusteringConfig(enabled=True, max_clients_per_cluster=2, min_clusters=1)
    payload = ClusteringInput(
        clients=(
            PreprocessedClientInput("t1", 0.05, 1000.0, 0.10),
            PreprocessedClientInput("t2", 0.15, 900.0, 0.20),
            PreprocessedClientInput("t3", 0.25, 800.0, 0.30),
            PreprocessedClientInput("t4", 0.35, 700.0, 0.40),
            PreprocessedClientInput("t5", 0.45, 600.0, 0.50),
        ),
        config=config,
        run_id=99,
        source_file_id=123,
    )

    result = clusterize(payload)

    assert result.algorithm_name == "kmeans"
    assert result.total_clients == 5
    assert result.total_clusters >= 3
    assert result.total_clusters <= 5
    assert sum(cluster.metrics.client_count for cluster in result.clusters) == 5
    assert all(cluster.metrics.client_count <= 2 for cluster in result.clusters)

    assigned_tokens = [
        payload.clients[index].token
        for index in range(len(payload.clients))
    ]
    assert sorted(assigned_tokens) == ["t1", "t2", "t3", "t4", "t5"]
    assert all(cluster.members == () for cluster in result.clusters)

    summary = summarize_for_simplex(result)
    assert len(summary) == result.total_clusters
    assert len(result.client_cluster_ids) == 5
    assert sum(result.client_cluster_ids) >= 5


def test_determine_k_respects_max_clients_per_cluster():
    assert determine_k(5, min_clusters=1, max_clients_per_cluster=2, n_clusters=None) == 3
