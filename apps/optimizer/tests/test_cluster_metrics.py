import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from clustering.models import ClusterMember
from clustering.metrics.cluster_metrics import calculate_cluster_metrics


def test_calculate_cluster_metrics_includes_risk_helpers():
    members = [
        ClusterMember(
            token="t1",
            product_pd=0.10,
            payment_capacity=1000.0,
            contract_propensity_score=0.20,
            cluster_id=1,
        ),
        ClusterMember(
            token="t2",
            product_pd=0.30,
            payment_capacity=500.0,
            contract_propensity_score=0.40,
            cluster_id=1,
        ),
    ]

    metrics = calculate_cluster_metrics(members)

    assert metrics.client_count == 2
    assert metrics.average_pd == 0.20
    assert metrics.average_score == 0.30
    assert metrics.average_capacity == 750.0
    assert metrics.pd_stddev > 0.0
    assert metrics.score_stddev > 0.0
    assert 0.0 <= metrics.risk_score <= 1.0
    assert metrics.risk_level in {"low", "medium", "high"}
    assert metrics.leverage_multiplier in {1.2, 1.0, 0.75}
