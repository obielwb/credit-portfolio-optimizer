import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import Client, ModelParameters
from algorithms import run_algorithm
from ingestion import parse_filter_flag


def _parameters(*, filter: bool = True) -> ModelParameters:
    return ModelParameters(filter=filter, enabled=False)


def test_parse_filter_flag_trata_1_como_ineligible():
    assert parse_filter_flag(1) is True
    assert parse_filter_flag(0) is False


def test_business_filter_zeros_limit_when_filter_flag_is_active():
    clients = [
        Client("apt", 0.08, 2000.0, 0.5, filter_flag=False),
        Client("inapt", 0.08, 2000.0, 0.5, filter_flag=True),
    ]

    limits = run_algorithm("simplex", clients, _parameters(filter=True))

    assert limits[0] > 0
    assert limits[1] == 0.0


def test_disabled_filter_does_not_block_active_filter_flag():
    clients = [
        Client("apt", 0.08, 2000.0, 0.5, filter_flag=False),
        Client("inapt", 0.08, 2000.0, 0.5, filter_flag=True),
    ]

    limits = run_algorithm("simplex", clients, _parameters(filter=False))

    assert limits[0] > 0
    assert limits[1] > 0


@pytest.mark.parametrize("algorithm", ["simplex", "simplex_ortools", "branch_bound"])
def test_constraint_filter_applies_to_all_algorithms(algorithm: str):
    clients = [Client("bloqueado", 0.05, 3000.0, 0.6, filter_flag=True)]

    limits = run_algorithm(algorithm, clients, _parameters(filter=True))

    assert limits == [0.0]
