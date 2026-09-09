

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any


def cluster_id_to_label(cluster_id: int) -> str:


    return f"Cluster {cluster_id}"


def resolve_return_grouping(clusters: list, clients: list) -> str:
    """Whether return grouping uses cohort_reference or run clusters."""

    if _clients_have_cohort(clients):
        return "cohort"
    if clusters:
        return "cluster"
    return "cohort"


def build_cohort_analysis(clusters: list, clients: list) -> list[dict[str, Any]]:


    if _clients_have_cohort(clients):
        return _analise_from_clients_cohort(clients)
    if clusters:
        return _analise_from_clusters(clusters, clients)
    return []


def build_return_by_cohort(
    clusters: list,
    clients: list,
    total_return: float,
) -> list[dict[str, Any]]:


    if total_return <= 0:
        return []

    if _clients_have_cohort(clients):
        return _return_from_clients_cohort(clients, total_return)
    if clusters:
        return _return_from_clusters(clusters, total_return)
    return []


def build_return_by_cohort_legacy(clusters: list, clients: list, total_return: float) -> list[dict[str, Any]]:


    items = build_return_by_cohort(clusters, clients, total_return)
    return [
        {
            "cohort_reference": item["cohort_reference"],
            "total_clients": item.get("total_clients") or 0,
            "total_return": item["total_return"],
        }
        for item in items
    ]


def _clients_have_cohort(clients: list) -> bool:
    """Check whether any client has a reference cohort."""
    return any(getattr(client, "cohort_reference", None) for client in clients)


def _analise_from_clusters(clusters: list, clients: list) -> list[dict[str, Any]]:

    limit_ratio = _client_limit_capacity_ratio(clients)
    rate_global = float(_calc_approval_rate(clients)) if clients else 0.0

    rows: list[dict[str, Any]] = []
    for cluster in sorted(clusters, key=lambda item: item.cluster_id):
        average_capacity = float(cluster.average_capacity)
        average_limit = average_capacity * limit_ratio if limit_ratio else 0.0
        rows.append(
            {
                "cohort": cluster_id_to_label(cluster.cluster_id),
                "client_count": int(cluster.total_clients),
                "average_capacity": average_capacity,
                "average_limit": average_limit,
                "approval_rate": rate_global,
            }
        )
    return rows


def _analise_from_clients_cohort(clients: list) -> list[dict[str, Any]]:

    grouped: dict[str, list] = defaultdict(list)
    for client in clients:
        cohort = getattr(client, "cohort_reference", None)
        if cohort:
            grouped[str(cohort)].append(client)

    rows: list[dict[str, Any]] = []
    for cohort in sorted(grouped):
        group = grouped[cohort]
        average_capacity = sum(float(c.payment_capacity) for c in group) / len(group)
        average_limit = sum(float(c.last_suggested_limit) for c in group) / len(group)
        rows.append(
            {
                "cohort": cohort,
                "client_count": len(group),
                "average_capacity": average_capacity,
                "average_limit": average_limit,
                "approval_rate": float(_calc_approval_rate(group)),
            }
        )
    return rows


def _return_from_clusters(clusters: list, total_return: float) -> list[dict[str, Any]]:
    """Distribute total return proportionally across clusters."""
    total_clients = sum(int(cluster.total_clients) for cluster in clusters)
    if total_clients <= 0:
        return []

    items: list[dict[str, Any]] = []
    for cluster in sorted(clusters, key=lambda item: item.cluster_id):
        share = int(cluster.total_clients) / total_clients
        items.append(
            {
                "cohort_reference": cluster_id_to_label(cluster.cluster_id),
                "total_return": total_return * share,
                "percentage": round(share * 100, 2),
                "total_clients": int(cluster.total_clients),
            }
        )
    return items


def _return_from_clients_cohort(
    clients: list,
    total_return: float,
) -> list[dict[str, Any]]:

    grouped: dict[str, list] = defaultdict(list)
    for client in clients:
        cohort = getattr(client, "cohort_reference", None)
        if cohort:
            grouped[str(cohort)].append(client)

    total_clients = sum(len(group) for group in grouped.values())
    if total_clients <= 0:
        return []

    items: list[dict[str, Any]] = []
    for cohort in sorted(grouped):
        group = grouped[cohort]
        share = len(group) / total_clients
        items.append(
            {
                "cohort_reference": cohort,
                "total_return": total_return * share,
                "percentage": round(share * 100, 2),
                "total_clients": len(group),
            }
        )
    return items


def _client_limit_capacity_ratio(clients: list) -> float:

    if not clients:
        return 0.0

    avg_limit = sum(float(client.last_suggested_limit) for client in clients) / len(
        clients
    )
    avg_capacity = sum(
        float(client.payment_capacity) for client in clients
    ) / len(clients)
    if avg_capacity <= 0:
        return 0.0
    return avg_limit / avg_capacity


def _calc_approval_rate(clients: list) -> Decimal:

    if not clients:
        return Decimal("0")
    approved = sum(1 for client in clients if client.last_suggested_limit > 0)
    return Decimal(approved) / Decimal(len(clients))


__all__ = [
    "build_cohort_analysis",
    "build_return_by_cohort",
    "build_return_by_cohort_legacy",
    "cluster_id_to_label",
    "resolve_return_grouping",
]
