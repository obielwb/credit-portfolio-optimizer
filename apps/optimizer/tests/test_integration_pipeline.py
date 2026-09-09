import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import ModelParameters
from pipeline import run_pipeline
from clustering import ClusteringConfig, ClusteringInput, PreprocessedClientInput
from ingestion import load_data, preprocess


def _parameters() -> ModelParameters:
    return ModelParameters()


def test_pipeline_with_example_csv():
    csv_path = Path(__file__).resolve().parents[1] / "examples" / "clients_analisados.csv"
    result = run_pipeline(csv_path, "simplex", _parameters())
    expected_clients = preprocess(load_data(csv_path))
    assert result.algorithm == "simplex"
    assert len(result.clients) == len(expected_clients)


def test_pipeline_with_clustering_input():
    clustering_input = ClusteringInput(
        clients=(
            PreprocessedClientInput("t1", 0.10, 1000.0, 0.20),
            PreprocessedClientInput("t2", 0.20, 900.0, 0.30),
        ),
        config=ClusteringConfig(enabled=True, max_clients_per_cluster=2, min_clusters=1),
        run_id=1,
        source_file_id=1,
    )

    parameters = ModelParameters(min_clusters=1)
    result = run_pipeline(None, "simplex", parameters, clustering_input=clustering_input)
    assert result.algorithm == "simplex"
    assert len(result.clients) == 2
    assert result.clients[0].suggested_limit == result.clients[1].suggested_limit
