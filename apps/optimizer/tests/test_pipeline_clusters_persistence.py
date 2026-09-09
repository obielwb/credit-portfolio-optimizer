import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import ModelParameters
from pipeline import run_pipeline
from clustering import ClusteringConfig, ClusteringInput, PreprocessedClientInput


def test_pipeline_returns_clusters_when_clustering_is_active():
    clustering_input = ClusteringInput(
        clients=(
            PreprocessedClientInput("t1", 0.10, 1000.0, 0.20),
            PreprocessedClientInput("t2", 0.20, 900.0, 0.30),
            PreprocessedClientInput("t3", 0.15, 950.0, 0.25),
        ),
        config=ClusteringConfig(enabled=True, max_clients_per_cluster=2, min_clusters=1),
    )
    parameters = ModelParameters(enabled=True, min_clusters=1)

    result = run_pipeline(
        None,
        "simplex",
        parameters,
        clustering_input=clustering_input,
    )

    assert len(result.clusters) >= 1
    assert sum(cluster.total_clients for cluster in result.clusters) == 3
    assert all(cluster.policy_name for cluster in result.clusters)


def test_pipeline_returns_no_clusters_when_clustering_is_disabled():
    parameters = ModelParameters(enabled=False)
    clients_input = ClusteringInput(
        clients=(PreprocessedClientInput("t1", 0.10, 1000.0, 0.20),),
        config=ClusteringConfig(enabled=False, max_clients_per_cluster=1000, min_clusters=1),
    )

    result = run_pipeline(
        None,
        "simplex",
        parameters,
        clustering_input=clients_input,
    )

    assert result.clusters == ()
