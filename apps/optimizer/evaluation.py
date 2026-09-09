





from __future__ import annotations

from math import floor

from models import (
    ClientEvaluation,
    Client,
    ModelParameters,
    PortfolioResult,
    ClientResult,
    ClusterResult,
)



MULTIPLIER_RANGES: list[tuple[float, float]] = [
    (0.10, 1.70),
    (0.15, 1.40),
    (0.20, 1.00),
    (0.30, 0.60),
    (float("inf"), 0.30),
]


def client_fails_business_filter(client: Client, parameters: ModelParameters) -> bool:


    if not parameters.filter:
        return False
    return client.filter_flag


def approved_limit_floor(parameters: ModelParameters) -> float:






    if parameters.min_limit > 0:
        return float(parameters.min_limit)
    return float(parameters.max_rejected_limit)


def apply_limit_postprocessing(limit: float, parameters: ModelParameters) -> float:
    """Apply the operational rule that maps limits in the prohibited range (0, floor) to zero."""

    value = float(limit)
    if value <= 0:
        return 0.0
    if value < approved_limit_floor(parameters):
        return 0.0
    return value


def apply_limit_postprocessing(
    limits: list[float],
    parameters: ModelParameters,
) -> list[float]:


    return [apply_limit_postprocessing(limit, parameters) for limit in limits]


def limit_e_approved(limit: float, parameters: ModelParameters) -> bool:


    return apply_limit_postprocessing(limit, parameters) >= approved_limit_floor(parameters)


def multiplier_por_pd(product_pd: float) -> float:








    for max_pd, multiplier in MULTIPLIER_RANGES:
        if product_pd <= max_pd:
            return multiplier
    return MULTIPLIER_RANGES[-1][1]


def calculate_max_client_limit(client: Client, parameters: ModelParameters) -> float:













    risk_ceiling = multiplier_por_pd(client.product_pd) * client.payment_capacity

    ceiling = min(parameters.max_limit, risk_ceiling)

    return floor(ceiling / parameters.limit_step) * parameters.limit_step


def evaluate_client_profitability(
    limit: float,
    client: Client,
    parameters: ModelParameters,
) -> ClientEvaluation:










    # Exposure at Default (EAD): limit * expected utilization rate
    ead = limit * parameters.utilization_rate

    income = (
        client.contract_propensity_score
        * ead
        * parameters.interchange
    ) * 12

    loss = parameters.lgd * client.product_pd * ead * client.contract_propensity_score

    return ClientEvaluation(
        client=client,
        limit_candidate=limit,
        expected_income=income,
        expected_loss=loss,
        expected_return=income - loss,
    )


def build_results(
    clients: list[Client],
    limits_otimos: list[float],
    parameters: ModelParameters,
    algorithm: str,
    clusters: tuple[ClusterResult, ...] = (),
) -> PortfolioResult:














    if len(clients) != len(limits_otimos):
        raise ValueError("The limit count must equal the client count.")

    results: list[ClientResult] = []
    for client, limit in zip(clients, limits_otimos):
        evaluation = evaluate_client_profitability(limit, client, parameters)
        results.append(
            ClientResult(
                client=client,
                suggested_limit=float(round(limit, 2)),
                expected_income=float(round(evaluation.expected_income, 2)),
                expected_loss=float(round(evaluation.expected_loss, 2)),
                expected_return=float(round(evaluation.expected_return, 2)),
            )
        )


    total_limit = sum(result.suggested_limit for result in results)
    total_income = sum(result.expected_income for result in results)
    total_loss = sum(result.expected_loss for result in results)
    total_return = sum(result.expected_return for result in results)

    default_rate = total_loss / total_limit if total_limit > 0 else 0.0

    return PortfolioResult(
        clients=results,
        total_limit=float(round(total_limit, 2)),
        total_income=float(round(total_income, 2)),
        total_loss=float(round(total_loss, 2)),
        total_return=float(round(total_return, 2)),
        financial_default_rate=float(round(default_rate, 6)),
        baseline_default_rate=parameters.baseline_default_rate,
        algorithm=algorithm,
        clusters=clusters,
    )
