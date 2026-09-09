"""Custom Simplex implementation for credit-limit portfolio optimization."""

from __future__ import annotations

from models import Client, ModelParameters
from evaluation import (
    apply_limit_postprocessing,
    calculate_max_client_limit,
    evaluate_client_profitability,
    client_fails_business_filter,
)
from progress import notify_progress
import numpy as np

from clustering.contracts import SimplexClusterSummary


def build_lp_problem(
    clients: list[Client],
    parameters: ModelParameters,
) -> tuple[list[float], list[list[float]], list[float]]:
    """Build the linear program ``max c^T x`` subject to ``Ax <= b`` and ``x >= 0``."""

    n = len(clients)

    unit_metrics = [
        evaluate_client_profitability(
            limit=1.0,
            client=client,
            parameters=parameters,
        )
        for client in clients
    ]

    c = [
        metrics.expected_return
        for metrics in unit_metrics
    ]

    A: list[list[float]] = []
    b: list[float] = []

    for idx, client in enumerate(clients):
        row = [0.0] * n
        row[idx] = 1.0
        A.append(row)
        b.append(calculate_max_client_limit(client, parameters))

    default_row = [
        metrics.expected_loss - parameters.baseline_default_rate
        for metrics in unit_metrics
    ]
    A.append(default_row)
    b.append(0.0)

    for idx, (expected_return, client) in enumerate(zip(c, clients)):
        if expected_return < 0 or client_fails_business_filter(client, parameters):
            zero_row = [0.0] * n
            zero_row[idx] = 1.0
            A.append(zero_row)
            b.append(0.0)

    return c, A, b


def optimize_simplex(clients: list[Client], parameters: ModelParameters) -> list[float]:
    """Maximize expected return subject to individual and portfolio risk constraints."""

    c, A, b = build_lp_problem(clients, parameters)

    notify_progress("calculating_constraints")

    x, _ = simplex(
        np.array(c),
        np.array(A),
        np.array(b),
    )

    notify_progress("validating_constraints")

    return apply_limit_postprocessing([float(xi) for xi in x], parameters)


def _representative_client(summary: SimplexClusterSummary) -> Client:
    """Build an average client that represents a cluster during optimization."""

    return Client(
        token=f"cluster-{summary.cluster_id}",
        product_pd=summary.average_pd,
        payment_capacity=summary.average_capacity,
        contract_propensity_score=summary.average_score,
        filter_flag=not summary.filter_flag_eligible,
    )


def build_cluster_lp_problem(
    summaries: list[SimplexClusterSummary],
    parameters: ModelParameters,
) -> tuple[list[float], list[list[float]], list[float]]:
    """Build an LP with one uniform-limit variable per cluster.

    The objective maximizes ``SUM_i expected_return_i * len(cluster_i)`` using
    the cluster representative's unit-limit economics.
    """

    n = len(summaries)
    if n == 0:
        return [], [], []

    representatives = [_representative_client(summary) for summary in summaries]
    unit_metrics = [
        evaluate_client_profitability(1.0, client, parameters)
        for client in representatives
    ]

    c = [
        summary.client_count * metrics.expected_return
        for summary, metrics in zip(summaries, unit_metrics)
    ]

    A: list[list[float]] = []
    b: list[float] = []

    for idx, (summary, representative) in enumerate(zip(summaries, representatives)):
        row = [0.0] * n
        row[idx] = 1.0
        A.append(row)

        ceiling = calculate_max_client_limit(representative, parameters) * summary.max_limit_factor
        b.append(ceiling)

    default_row = [
        summary.client_count
        * (metrics.expected_loss - parameters.baseline_default_rate)
        for summary, metrics in zip(summaries, unit_metrics)
    ]
    A.append(default_row)
    b.append(0.0)

    for idx, (expected_return, representative) in enumerate(zip(c, representatives)):
        if expected_return < 0 or client_fails_business_filter(representative, parameters):
            zero_row = [0.0] * n
            zero_row[idx] = 1.0
            A.append(zero_row)
            b.append(0.0)

    return c, A, b


def optimize_clusters_simplex(
    summaries: list[SimplexClusterSummary],
    parameters: ModelParameters,
) -> list[float]:
    """Optimize one limit per cluster with the custom Simplex solver."""

    c, A, b = build_cluster_lp_problem(summaries, parameters)
    if not c:
        return []

    notify_progress("calculating_constraints")

    x, _ = simplex(
        np.array(c),
        np.array(A),
        np.array(b),
    )

    notify_progress("validating_constraints")

    return apply_limit_postprocessing([float(xi) for xi in x], parameters)


def simplex(c, A, b):
    """Solve ``max c^T x`` subject to ``Ax <= b`` and ``x >= 0``.

    Returns the optimal decision vector and objective value.
    """

    m, n = A.shape  # Rows and columns in A


    tableau = np.zeros((m + 1, n + m + 1))

    # Insere a matriz A
    tableau[:m, :n] = A  # Coloca A no tableau


    tableau[:m, n:n+m] = np.eye(m)


    tableau[:m, -1] = b


    tableau[-1, :n] = -c

    notify_progress("tableau_calculation")

    first_iteration = True
    while True:
        if first_iteration:
            notify_progress("generating_recommendations")
            first_iteration = False


        pivot_col = np.argmin(tableau[-1, :-1])

        if tableau[-1, pivot_col] >= -1e-10:
            break


        ratios = []
        for i in range(m):
            if tableau[i, pivot_col] > 1e-10:
                ratios.append(tableau[i, -1] / tableau[i, pivot_col])
            else:
                ratios.append(np.inf)

        pivot_row = np.argmin(ratios)

        if ratios[pivot_row] == np.inf:
            raise RuntimeError("The linear program is unbounded.")

        # Pivotamento: updates o tableau
        pivot = tableau[pivot_row, pivot_col]
        tableau[pivot_row, :] /= pivot

        for i in range(m + 1):
            if i != pivot_row:
                tableau[i, :] -= tableau[i, pivot_col] * tableau[pivot_row, :]


    x = np.zeros(n)
    for column in range(n):
        column_tableau = tableau[:m, column]  
        unit_rows = np.where(np.isclose(column_tableau, 1.0, atol=1e-9))[0]
        if len(unit_rows) != 1:
            continue

        row = unit_rows[0]
        remaining_rows = np.delete(column_tableau, row)
        if np.all(np.isclose(remaining_rows, 0.0, atol=1e-9)):
            x[column] = tableau[row, -1]

    z = tableau[-1, -1]

    return x, z
