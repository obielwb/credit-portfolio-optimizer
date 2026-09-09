

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from evaluation import (
    apply_limit_postprocessing,
    apply_limit_postprocessing,
    limit_e_approved,
    approved_limit_floor,
)
from models import Client, ModelParameters
from pipeline import run_pipeline


def test_floor_uses_max_rejected_limit_when_minimum_is_zero():
    p = ModelParameters(min_limit=0.0, max_rejected_limit=200.0)
    assert approved_limit_floor(p) == 200.0


def test_floor_uses_min_limit_when_provided():
    p = ModelParameters(min_limit=150.0, max_rejected_limit=200.0)
    assert approved_limit_floor(p) == 150.0


def test_zona_proibida_vira_zero():
    p = ModelParameters(min_limit=0.0, max_rejected_limit=200.0)
    assert apply_limit_postprocessing(0.0, p) == 0.0
    assert apply_limit_postprocessing(50.0, p) == 0.0
    assert apply_limit_postprocessing(199.99, p) == 0.0
    assert apply_limit_postprocessing(200.0, p) == 200.0
    assert apply_limit_postprocessing(5000.0, p) == 5000.0


def test_limit_e_approved():
    p = ModelParameters(min_limit=0.0, max_rejected_limit=200.0)
    assert not limit_e_approved(0.0, p)
    assert not limit_e_approved(100.0, p)
    assert limit_e_approved(200.0, p)


def test_simplex_postprocessing_rejects_prohibited_range():


    p = ModelParameters(min_limit=0.0, max_rejected_limit=200.0, enabled=True)
    clients = [
        Client("bom", 0.05, 5000.0, 0.5),
        Client("ruim", 0.55, 400.0, 0.03),
    ]
    result = run_pipeline(None, "simplex", p, clients=clients)
    for rc in result.clients:
        limit = rc.suggested_limit
        assert limit == 0.0 or limit >= 200.0, f"invalid limit in the prohibited range: {limit}"


def test_mixed_portfolio_does_not_approve_every_client():


    from perf_config import generate_benchmark_clients, parameters_benchmark

    p = parameters_benchmark()
    clients = generate_benchmark_clients(2000, seed=42)
    result = run_pipeline(None, "simplex", p, clients=clients)
    approved = sum(1 for c in result.clients if c.suggested_limit >= 200.0)
    denied = sum(1 for c in result.clients if c.suggested_limit == 0.0)
    rate = approved / len(clients)
    assert denied > 0, "Expected at least one denied client with realistic data"
    assert rate < 1.0, f"Unrealistic approval rate: {rate:.1%}"
