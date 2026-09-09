

from __future__ import annotations

from statistics import fmean, pstdev

import numpy as np

from ..models import ClusterMember, ClusterMetrics


def calculate_cluster_metrics(members: list[ClusterMember]) -> ClusterMetrics:


    if not members:
        raise ValueError("Metrics cannot be calculated for an empty cluster.")

    member_count = len(members)
    return calculate_cluster_metrics_from_arrays(
        np.fromiter(
            (member.product_pd for member in members),
            dtype=np.float64,
            count=member_count,
        ),
        np.fromiter(
            (member.contract_propensity_score for member in members),
            dtype=np.float64,
            count=member_count,
        ),
        np.fromiter(
            (member.payment_capacity for member in members),
            dtype=np.float64,
            count=member_count,
        ),
    )


def calculate_cluster_metrics_from_arrays(
    pd_values: np.ndarray,
    score_values: np.ndarray,
    capacity_values: np.ndarray,
) -> ClusterMetrics:


    count = int(len(pd_values))
    if count == 0:
        raise ValueError("Metrics cannot be calculated for an empty cluster.")

    average_pd = round(float(np.mean(pd_values)), 10)
    average_score = round(float(np.mean(score_values)), 10)
    average_capacity = round(float(np.mean(capacity_values)), 10)
    pd_stddev = round(float(np.std(pd_values)), 10) if count > 1 else 0.0
    score_stddev = round(float(np.std(score_values)), 10) if count > 1 else 0.0
    risk_score = round(_calculate_risk_score(average_pd, average_score, pd_stddev), 10)
    risk_level, leverage_multiplier = _derive_risk_profile(risk_score)

    return ClusterMetrics(
        client_count=count,
        average_pd=average_pd,
        average_score=average_score,
        average_capacity=average_capacity,
        pd_stddev=pd_stddev,
        score_stddev=score_stddev,
        risk_score=risk_score,
        risk_level=risk_level,
        leverage_multiplier=leverage_multiplier,
    )


def _calculate_risk_score(
    average_pd: float, average_score: float, pd_stddev: float
) -> float:


    raw_score = (average_pd * 0.7) + ((1.0 - average_score) * 0.2) + (pd_stddev * 0.1)
    return max(0.0, min(1.0, raw_score))


def _derive_risk_profile(risk_score: float) -> tuple[str, float]:


    if risk_score < 0.20:
        return "low", 1.20
    if risk_score < 0.45:
        return "medium", 1.00
    return "high", 0.75


__all__ = ["calculate_cluster_metrics", "calculate_cluster_metrics_from_arrays"]
