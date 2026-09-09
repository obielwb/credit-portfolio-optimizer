

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from ..contracts import ClusteringInput
from ..feature_engineering import FeatureEngineeringResult, engineer_features
from ..metrics.cluster_metrics import calculate_cluster_metrics_from_arrays
from ..models import ClusterResult, ClusteringResult
from ..policies.leverage_policy import build_cluster_policy
from ..validators.clustering_validator import validate_clustering_input
from .kmeans_core import (
    MAIN_KMEANS_MAX_ITERS,
    MAIN_KMEANS_TOL,
    determine_k,
    enforce_clustering_constraints,
    fit_kmeans,
    relabel_contiguous,
)


class KMeansClusterAlgorithm:


    name = "kmeans"
    version = "2.2.0"

    def execute(self, payload: ClusteringInput) -> ClusteringResult:









        validate_clustering_input(payload)
        engineered = engineer_features(payload)

        if not payload.config.enabled:
            return self._build_single_cluster_result(payload, engineered)

        k = determine_k(
            len(payload.clients),
            min_clusters=payload.config.min_clusters,
            max_clients_per_cluster=payload.config.max_clients_per_cluster,
            n_clusters=payload.config.n_clusters,
        )
        feature_matrix = np.asarray(
            engineered.feature_matrix_ndarray, dtype=np.float32
        )
        seed = self._seed(payload)
        labels = fit_kmeans(
            feature_matrix,
            k,
            max_iters=MAIN_KMEANS_MAX_ITERS,
            tol=MAIN_KMEANS_TOL,
            seed=seed,
        )
        min_clusters = min(max(1, payload.config.min_clusters), len(payload.clients))
        labels = enforce_clustering_constraints(
            labels,
            feature_matrix,
            min_clusters=min_clusters,
            max_size=payload.config.max_clients_per_cluster,
            seed=seed,
        )
        labels = relabel_contiguous(labels)

        clusters, client_cluster_ids = self._build_clusters_from_labels(
            engineered, labels
        )

        return ClusteringResult(
            clusters=clusters,
            config=payload.config,
            algorithm_name=self.name,
            algorithm_version=self.version,
            total_clients=len(payload.clients),
            total_clusters=len(clusters),
            client_cluster_ids=client_cluster_ids,
        )

    def _seed(self, payload: ClusteringInput) -> int:


        run_id = payload.run_id or 0
        source_file_id = payload.source_file_id or 0
        return 42 + run_id * 997 + source_file_id * 17

    def _build_clusters_from_labels(
        self,
        engineered: FeatureEngineeringResult,
        labels: np.ndarray,
    ) -> tuple[list[ClusterResult], tuple[int, ...]]:










        labels = np.asarray(labels, dtype=np.int32)
        clients = engineered.clients
        n = len(clients)

        pd_arr = np.fromiter(
            (client.source.product_pd for client in clients),
            dtype=np.float64,
            count=n,
        )
        score_arr = np.fromiter(
            (client.source.contract_propensity_score for client in clients),
            dtype=np.float64,
            count=n,
        )
        cap_arr = np.fromiter(
            (client.source.payment_capacity for client in clients),
            dtype=np.float64,
            count=n,
        )

        client_cluster_ids = tuple(int(labels[index]) + 1 for index in range(n))
        created_at = datetime.now(timezone.utc)
        clusters: list[ClusterResult] = []

        for cluster_index in np.unique(labels):
            mask = labels == cluster_index
            cluster_id = int(cluster_index) + 1
            metrics = calculate_cluster_metrics_from_arrays(
                pd_arr[mask],
                score_arr[mask],
                cap_arr[mask],
            )
            policy = build_cluster_policy(metrics)
            clusters.append(
                ClusterResult(
                    cluster_id=cluster_id,
                    metrics=metrics,
                    policy=policy,
                    created_at=created_at,
                )
            )

        clusters.sort(key=lambda cluster: cluster.cluster_id)
        return clusters, client_cluster_ids

    def _build_single_cluster_result(
        self,
        payload: ClusteringInput,
        engineered: FeatureEngineeringResult,
    ) -> ClusteringResult:


        n = len(engineered.clients)
        pd_arr = np.fromiter(
            (c.source.product_pd for c in engineered.clients),
            dtype=np.float64,
            count=n,
        )
        score_arr = np.fromiter(
            (c.source.contract_propensity_score for c in engineered.clients),
            dtype=np.float64,
            count=n,
        )
        cap_arr = np.fromiter(
            (c.source.payment_capacity for c in engineered.clients),
            dtype=np.float64,
            count=n,
        )
        metrics = calculate_cluster_metrics_from_arrays(pd_arr, score_arr, cap_arr)
        policy = build_cluster_policy(metrics)
        cluster = ClusterResult(
            cluster_id=1,
            metrics=metrics,
            policy=policy,
            created_at=datetime.now(timezone.utc),
        )
        client_cluster_ids = tuple(1 for _ in engineered.clients)
        return ClusteringResult(
            clusters=[cluster],
            config=payload.config,
            algorithm_name=self.name,
            algorithm_version=self.version,
            total_clients=len(payload.clients),
            total_clusters=1,
            client_cluster_ids=client_cluster_ids,
        )


__all__ = ["KMeansClusterAlgorithm"]
