import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import Client, ModelParameters
from algorithms import run_algorithm
import pytest


def _parameters() -> ModelParameters:
    return ModelParameters()


def test_run_algorithm_simplex_returns_limits_for_each_client():
    clients = [
        Client(token="a", product_pd=0.1, payment_capacity=1000.0, contract_propensity_score=0.2),
        Client(token="b", product_pd=0.2, payment_capacity=900.0, contract_propensity_score=0.3),
    ]

    limits = run_algorithm("simplex", clients, _parameters())
    assert isinstance(limits, list)
    assert len(limits) == len(clients)


def test_run_algorithm_simplex_ortools_returns_limits_for_each_client():
    clients = [
        Client(token="a", product_pd=0.1, payment_capacity=1000.0, contract_propensity_score=0.2),
        Client(token="b", product_pd=0.2, payment_capacity=900.0, contract_propensity_score=0.3),
    ]

    limits = run_algorithm("simplex_ortools", clients, _parameters())
    assert isinstance(limits, list)
    assert len(limits) == len(clients)


def test_run_algorithm_unknown_raises():
    clients = []
    with pytest.raises(ValueError):
        run_algorithm("no_such_algo", clients, _parameters())
