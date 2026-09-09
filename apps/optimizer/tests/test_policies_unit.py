import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from clustering.policies.leverage_policy import build_cluster_policy, LEVERAGE_POLICY_TABLE
from clustering.models import ClusterMetrics


def _metrics_with_risk(risk_score: float) -> ClusterMetrics:
    return ClusterMetrics(
        client_count=10,
        average_pd=0.2,
        average_score=0.3,
        average_capacity=1000.0,
        pd_stddev=0.0,
        score_stddev=0.0,
        risk_score=risk_score,
        risk_level="medium",
        leverage_multiplier=1.0,
    )


def test_build_cluster_policy_boundaries():
    # Test each range in the table
    edges = [0.0, 0.2, 0.45, 0.9]
    expected = [r.policy_name for r in LEVERAGE_POLICY_TABLE]
    results = [build_cluster_policy(_metrics_with_risk(e)).policy_name for e in edges]
    # Since ranges are left-inclusive and right-exclusive, map expectations accordingly
    assert results[0] == expected[0]
    assert results[1] == expected[1]
    assert results[2] == expected[2]
