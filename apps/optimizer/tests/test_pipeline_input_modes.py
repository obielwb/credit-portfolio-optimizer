import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from clustering import ClusteringConfig, ClusteringInput, PreprocessedClientInput
from ingestion import load_data, preprocess
from models import Client, ModelParameters
from pipeline import run_pipeline


def _parameters() -> ModelParameters:
    return ModelParameters(
        interchange=0.0175,
        lgd=0.80,
        min_limit=0.0,
        max_rejected_limit=200.0,
        max_limit=25000.0,
        baseline_default_rate=0.0553,
        limit_step=50.0,
        utilization_rate=0.70,
    )


def test_pipeline_accepts_preprocessed_clients_without_file():
    clients = [
        Client(token="t1", product_pd=0.10, payment_capacity=1000.0, contract_propensity_score=0.20),
        Client(token="t2", product_pd=0.20, payment_capacity=900.0, contract_propensity_score=0.30),
    ]

    result = run_pipeline(
        None,
        "simplex",
        _parameters(),
        clients=clients,
    )

    assert len(result.clients) == 2
    assert result.algorithm == "simplex"


def test_pipeline_accepts_cluster_input_from_queue_without_file():
    clustering_input = ClusteringInput(
        clients=(
            PreprocessedClientInput("t1", 0.10, 1000.0, 0.20),
            PreprocessedClientInput("t2", 0.20, 900.0, 0.30),
        ),
        config=ClusteringConfig(enabled=True, max_clients_per_cluster=2),
        run_id=10,
        source_file_id=99,
    )

    result = run_pipeline(
        None,
        "simplex",
        _parameters(),
        clustering_input=clustering_input,
    )

    assert len(result.clients) == 2
    assert result.algorithm == "simplex"
    assert [client.client.token for client in result.clients] == ["t1", "t2"]


def test_pipeline_processes_example_csv_via_path():
    csv_path = Path(__file__).resolve().parents[1] / "examples" / "clients_analisados.csv"

    result = run_pipeline(
        csv_path,
        "simplex",
        _parameters(),
    )

    expected_clients = preprocess(load_data(csv_path))

    assert result.algorithm == "simplex"
    assert len(result.clients) == len(expected_clients)
    assert [client.client.token for client in result.clients[:3]] == [
        client.token for client in expected_clients[:3]
    ]
