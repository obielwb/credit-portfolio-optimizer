import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from clustering.metrics.cluster_metrics import calculate_cluster_metrics
from clustering.models import ClusterMember


def test_calculate_cluster_metrics_basic():
    members = [
        ClusterMember(token="t1", product_pd=0.1, payment_capacity=1000.0, contract_propensity_score=0.2, cluster_id=1),
        ClusterMember(token="t2", product_pd=0.2, payment_capacity=900.0, contract_propensity_score=0.3, cluster_id=1),
    ]

    metrics = calculate_cluster_metrics(members)
    assert metrics.client_count == 2
    assert round(metrics.average_pd, 6) == round((0.1 + 0.2) / 2, 6)
    assert round(metrics.average_score, 6) == round((0.2 + 0.3) / 2, 6)
