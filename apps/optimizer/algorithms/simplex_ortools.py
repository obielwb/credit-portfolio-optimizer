






from __future__ import annotations

from ortools.linear_solver import pywraplp

from evaluation import apply_limit_postprocessing
from models import Client, ModelParameters
from progress import notify_progress

from clustering.contracts import SimplexClusterSummary

from .simplex import build_lp_problem, build_cluster_lp_problem


def _solve_lp_ortools(
    c: list[float],
    A: list[list[float]],
    b: list[float],
) -> list[float]:


    n = len(c)
    solver = pywraplp.Solver.CreateSolver("GLOP")
    if not solver:
        raise RuntimeError("The OR-Tools GLOP solver could not be created.")

    variables = [
        solver.NumVar(0.0, solver.infinity(), f"L_{i}")
        for i in range(n)
    ]

    objective = solver.Objective()
    for i, coef in enumerate(c):
        objective.SetCoefficient(variables[i], coef)
    objective.SetMaximization()

    for row, rhs in zip(A, b):
        constraint = solver.Constraint(-solver.infinity(), rhs)
        for i, coef in enumerate(row):
            if coef != 0:
                constraint.SetCoefficient(variables[i], coef)

    status = solver.Solve()
    if status != pywraplp.Solver.OPTIMAL:
        raise RuntimeError("The OR-Tools solver did not find an optimal solution.")

    return [variable.solution_value() for variable in variables]


def optimize_simplex_ortools(
    clients: list[Client],
    parameters: ModelParameters,
) -> list[float]:


    if not clients:
        return []

    c, A, b = build_lp_problem(clients, parameters)

    notify_progress("calculating_constraints")

    x = _solve_lp_ortools(c, A, b)

    notify_progress("validating_constraints")

    return apply_limit_postprocessing([float(xi) for xi in x], parameters)


def optimize_clusters_simplex_ortools(
    summaries: list[SimplexClusterSummary],
    parameters: ModelParameters,
) -> list[float]:


    c, A, b = build_cluster_lp_problem(summaries, parameters)
    if not c:
        return []

    notify_progress("calculating_constraints")

    x = _solve_lp_ortools(c, A, b)

    notify_progress("validating_constraints")

    return apply_limit_postprocessing([float(xi) for xi in x], parameters)
