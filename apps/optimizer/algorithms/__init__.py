






from __future__ import annotations

from collections.abc import Callable

from models import Client, ModelParameters

from .simplex import optimize_simplex
from .simplex_ortools import optimize_simplex_ortools
from .branch_bound import optimize_branch_and_bound


OptimizationAlgorithm = Callable[[list[Client], ModelParameters], list[float]]


ALGORITHMS: dict[str, OptimizationAlgorithm] = {
    "simplex": optimize_simplex,
    "simplex_ortools": optimize_simplex_ortools,
    "branch_bound": optimize_branch_and_bound,
}


def run_algorithm(
    name: str,
    clients: list[Client],
    parameters: ModelParameters,
) -> list[float]:













    try:
        algorithm = ALGORITHMS[name]
    except KeyError as error:
        available = ", ".join(sorted(ALGORITHMS))
        raise ValueError(f"Unknown algorithm: {name}. Options: {available}") from error

    limits = algorithm(clients, parameters)
    if len(limits) != len(clients):
        raise ValueError("The algorithm must return one limit per client.")
    return limits
