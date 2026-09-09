

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from src.services.cohort_analytics import (
    build_cohort_analysis,
    build_return_by_cohort,
    cluster_id_to_label,
    resolve_return_grouping,
)


def _cluster(cluster_id: int, total_clients: int, average_capacity: float):
    return SimpleNamespace(
        cluster_id=cluster_id,
        total_clients=total_clients,
        average_capacity=average_capacity,
    )


def _client(token: str, cohort: str | None, limit: float, capacity: float):
    return SimpleNamespace(
        token=token,
        cohort_reference=cohort,
        last_suggested_limit=limit,
        payment_capacity=capacity,
    )


def test_cluster_id_to_label():
    assert cluster_id_to_label(1) == "Cluster 1"
    assert cluster_id_to_label(3) == "Cluster 3"


def test_resolve_return_grouping_prefers_cohort():
    clusters = [_cluster(1, 10, 1000.0)]
    clients = [_client("a", "M1", 1000.0, 2000.0)]
    assert resolve_return_grouping(clusters, clients) == "cohort"


def test_resolve_return_grouping_uses_cluster_without_cohort():
    clusters = [_cluster(1, 10, 1000.0)]
    clients = [_client("a", None, 1000.0, 2000.0)]
    assert resolve_return_grouping(clusters, clients) == "cluster"


def test_build_cohort_analysis_from_clusters():
    clusters = [
        _cluster(1, 100, 10000.0),
        _cluster(2, 50, 8000.0),
    ]
    clients = [
        _client("a", None, 5000.0, 10000.0),
        _client("b", None, 4000.0, 8000.0),
    ]

    rows = build_cohort_analysis(clusters, clients)

    assert len(rows) == 2
    assert rows[0]["cohort"] == "Cluster 1"
    assert rows[0]["client_count"] == 100
    assert rows[0]["average_capacity"] == 10000.0


def test_build_return_by_cohort_from_clusters():
    clusters = [
        _cluster(1, 100, 10000.0),
        _cluster(2, 100, 8000.0),
    ]

    items = build_return_by_cohort(clusters, [], 1000.0)

    assert len(items) == 2
    assert items[0]["cohort_reference"] == "Cluster 1"
    assert items[0]["total_return"] == 500.0
    assert items[0]["percentage"] == 50.0


def test_build_cohort_analysis_from_clients_cohort_ref():
    clients = [
        _client("a", "M1", 5000.0, 10000.0),
        _client("b", "M1", 0.0, 9000.0),
        _client("c", "M2", 3000.0, 7000.0),
    ]

    rows = build_cohort_analysis([], clients)

    assert len(rows) == 2
    assert rows[0]["cohort"] == "M1"
    assert rows[0]["client_count"] == 2
    assert rows[0]["approval_rate"] == 0.5


def test_build_return_by_cohort_prefers_clients_cohort_over_clusters():
    clusters = [_cluster(1, 10, 1000.0)]
    clients = [
        _client("a", "M3", 1000.0, 2000.0),
        _client("b", "M2", 1000.0, 2000.0),
    ]

    items = build_return_by_cohort(clusters, clients, 200.0)

    assert len(items) == 2
    assert {item["cohort_reference"] for item in items} == {"M2", "M3"}


def test_build_cohort_analysis_prefers_clients_cohort_over_clusters():
    clusters = [
        _cluster(1, 100, 10000.0),
        _cluster(2, 50, 8000.0),
    ]
    clients = [
        _client("a", "M1", 5000.0, 10000.0),
        _client("b", "M1", 4000.0, 9000.0),
    ]

    rows = build_cohort_analysis(clusters, clients)

    assert len(rows) == 1
    assert rows[0]["cohort"] == "M1"
    assert rows[0]["client_count"] == 2
