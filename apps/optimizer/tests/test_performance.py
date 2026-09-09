

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from perf_config import (
    generate_benchmark_clients,
    parameters_benchmark,
    validate_active_clustering,
)
from pipeline import run_pipeline
from evaluation import approved_limit_floor


@pytest.mark.parametrize(
    "n, max_seconds",
    [
        (100, 10.0),
        (1000, 30.0),
        (10000, 120.0),
        (100000, 900.0),
        (1_000_000, 3600.0),
    ],
)
def test_simplex_performance_with_clustering(n: int, max_seconds: float):








    run_heavy = os.getenv("RUN_HEAVY_PERF_TESTS") in ("1", "true", "TRUE", "yes", "Y")
    run_stress = os.getenv("RUN_STRESS_TESTS") in ("1", "true", "TRUE", "yes", "Y")
    if n > 1000 and not run_heavy:
        pytest.skip(
            f"Skipping heavy perf test for n={n}; set RUN_HEAVY_PERF_TESTS=1 to run"
        )
    if n >= 1_000_000 and not run_stress:
        pytest.skip(f"Skipping n={n}; set RUN_STRESS_TESTS=1 to run")

    parameters = parameters_benchmark()
    assert parameters.enabled is True

    start = time.monotonic()
    result = run_pipeline(
        None,
        "simplex",
        parameters,
        clients=generate_benchmark_clients(n),
    )
    elapsed = time.monotonic() - start

    assert len(result.clients) == n
    validate_active_clustering(result, parameters, n)
    floor = approved_limit_floor(parameters)
    for rc in result.clients:
        limit = rc.suggested_limit
        assert limit == 0.0 or limit >= floor
    assert elapsed < max_seconds, (
        f"Performance regression: n={n} took {elapsed:.2f}s (limit {max_seconds}s)"
    )
