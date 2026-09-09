

from __future__ import annotations

from dataclasses import dataclass

from ..models import ClusterPolicy, ClusterMetrics


@dataclass(frozen=True)
class LeveragePolicyRule:


    min_risk_score: float
    max_risk_score: float
    policy_name: str
    policy_version: str
    risk_band: str
    max_limit_factor: float
    leverage_table_reference: str


LEVERAGE_POLICY_TABLE: tuple[LeveragePolicyRule, ...] = (
    LeveragePolicyRule(
        min_risk_score=0.0,
        max_risk_score=0.2,
        policy_name="conservative",
        policy_version="1.0.0",
        risk_band="A",
        max_limit_factor=1.20,
        leverage_table_reference="leverage_low",
    ),
    LeveragePolicyRule(
        min_risk_score=0.2,
        max_risk_score=0.45,
        policy_name="balanced",
        policy_version="1.0.0",
        risk_band="B",
        max_limit_factor=1.00,
        leverage_table_reference="leverage_medium",
    ),
    LeveragePolicyRule(
        min_risk_score=0.45,
        max_risk_score=1.0,
        policy_name="restrictive",
        policy_version="1.0.0",
        risk_band="C",
        max_limit_factor=0.75,
        leverage_table_reference="leverage_high",
    ),
)


def build_cluster_policy(metrics: ClusterMetrics) -> ClusterPolicy:







    rule = _resolve_policy_rule(metrics.risk_score)
    return ClusterPolicy(
        policy_name=rule.policy_name,
        policy_version=rule.policy_version,
        risk_band=rule.risk_band,
        max_limit_factor=rule.max_limit_factor,
        leverage_table_reference=rule.leverage_table_reference,
    )


def _resolve_policy_rule(risk_score: float) -> LeveragePolicyRule:









    for rule in LEVERAGE_POLICY_TABLE:
        if rule.min_risk_score <= risk_score < rule.max_risk_score:
            return rule
    return LEVERAGE_POLICY_TABLE[-1]


__all__ = ["LEVERAGE_POLICY_TABLE", "LeveragePolicyRule", "build_cluster_policy"]
