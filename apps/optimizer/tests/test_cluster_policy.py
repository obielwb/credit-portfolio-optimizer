import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from clustering.models import ClusterMetrics
from clustering.policies import LEVERAGE_POLICY_TABLE, build_cluster_policy


def test_leverage_policy_table_has_three_bands():
    assert len(LEVERAGE_POLICY_TABLE) == 3


def test_build_cluster_policy_for_low_risk():
    metrics = ClusterMetrics(
        client_count=2,
        average_pd=0.05,
        average_score=0.90,
        average_capacity=1000.0,
        pd_stddev=0.0,
        score_stddev=0.0,
        risk_score=0.10,
        risk_level="low",
        leverage_multiplier=1.20,
    )

    policy = build_cluster_policy(metrics)

    assert policy.policy_name == "conservative"
    assert policy.risk_band == "A"
    assert policy.max_limit_factor == 1.20
    assert policy.leverage_table_reference == "leverage_low"


def test_build_cluster_policy_for_high_risk():
    metrics = ClusterMetrics(
        client_count=2,
        average_pd=0.30,
        average_score=0.40,
        average_capacity=700.0,
        pd_stddev=0.15,
        score_stddev=0.10,
        risk_score=0.70,
        risk_level="high",
        leverage_multiplier=0.75,
    )

    policy = build_cluster_policy(metrics)

    assert policy.policy_name == "restrictive"
    assert policy.risk_band == "C"
    assert policy.max_limit_factor == 0.75
    assert policy.leverage_table_reference == "leverage_high"
