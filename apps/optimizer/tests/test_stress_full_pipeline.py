import os
import sys
import time

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import Client
from perf_config import parameters_benchmark, validate_active_clustering
from pipeline import run_pipeline


def test_full_pipeline_stress_1m_clients_manual_only():










    if os.getenv("RUN_STRESS_TESTS") not in ("1", "true", "TRUE", "yes", "Y"):
        pytest.skip("Skipping stress test; set RUN_STRESS_TESTS=1 to run")

    n = int(os.getenv("STRESS_CLIENTS", "1000000"))
    max_seconds = float(os.getenv("STRESS_MAX_SECONDS", "1800"))

    clients = [
        Client(
            token=str(i),
            product_pd=0.1 + (i % 10) * 0.01,
            payment_capacity=1000.0 + i,
            contract_propensity_score=0.2,
        )
        for i in range(n)
    ]

    parameters = parameters_benchmark()

    start = time.monotonic()
    result = run_pipeline(None, "simplex", parameters, clients=clients)
    elapsed = time.monotonic() - start

    assert len(result.clients) == n
    validate_active_clustering(result, parameters, n)
    assert elapsed < max_seconds, (
        f"Stress regression: n={n} took {elapsed:.2f}s (limit {max_seconds}s)"
    )
