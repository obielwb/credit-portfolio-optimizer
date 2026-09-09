

from __future__ import annotations

from .contracts import ClusteringInput, SimplexClusterSummary
from .algorithms.kmeans import KMeansClusterAlgorithm
from .algorithms import STRATEGY_REGISTRY
from models import ClusterResult

from .models import ClusterMember, ClusteringResult
from .validators.clustering_validator import validate_clustering_input


def clusterize(payload: ClusteringInput) -> ClusteringResult:





    validate_clustering_input(payload)

    strategy = (payload.config.strategy or "").lower()
    AlgorithmClass = STRATEGY_REGISTRY.get(strategy)
    if AlgorithmClass is None:

        AlgorithmClass = KMeansClusterAlgorithm

    algorithm = AlgorithmClass()
    return algorithm.execute(payload)


def summarize_for_simplex(result: ClusteringResult) -> list[SimplexClusterSummary]:


    return [SimplexClusterSummary.from_cluster_result(cluster) for cluster in result.clusters]


def materialize_cluster_members(
    result: ClusteringResult,
    clients: tuple,
) -> ClusteringResult:


    if not result.client_cluster_ids or not clients:
        return result
    if all(cluster.members for cluster in result.clusters):
        return result

    by_cluster: dict[int, list[ClusterMember]] = {}
    for index, cluster_id in enumerate(result.client_cluster_ids):
        source = clients[index]
        by_cluster.setdefault(cluster_id, []).append(
            ClusterMember(
                token=source.token,
                product_pd=float(source.product_pd),
                payment_capacity=float(source.payment_capacity),
                contract_propensity_score=float(source.contract_propensity_score),
                cluster_id=cluster_id,
            )
        )

    filled_clusters = []
    for cluster in result.clusters:
        members = tuple(by_cluster.get(cluster.cluster_id, ()))
        filled_clusters.append(
            type(cluster)(
                cluster_id=cluster.cluster_id,
                metrics=cluster.metrics,
                policy=cluster.policy,
                created_at=cluster.created_at,
                members=members,
            )
        )

    return ClusteringResult(
        clusters=filled_clusters,
        config=result.config,
        algorithm_name=result.algorithm_name,
        algorithm_version=result.algorithm_version,
        total_clients=result.total_clients,
        total_clusters=result.total_clusters,
        client_cluster_ids=result.client_cluster_ids,
    )


def clusters_for_persistence(result: ClusteringResult) -> tuple[ClusterResult, ...]:


    return tuple(
        ClusterResult(
            cluster_id=cluster.cluster_id,
            total_clients=cluster.metrics.client_count,
            average_pd=cluster.metrics.average_pd,
            average_score=cluster.metrics.average_score,
            average_capacity=cluster.metrics.average_capacity,
            policy_name=cluster.policy.policy_name,
            leverage_multiplier=cluster.metrics.leverage_multiplier,
        )
        for cluster in result.clusters
    )


__all__ = [
    "clusterize",
    "clusters_for_persistence",
    "materialize_cluster_members",
    "summarize_for_simplex",
]
