

from __future__ import annotations

from math import ceil

import numpy as np


MAIN_KMEANS_MAX_ITERS = 50
MAIN_KMEANS_TOL = 1e-4

NESTED_KMEANS_MAX_ITERS = 30

LARGE_DATASET_MINIBATCH_N = 50_000
LARGE_DATASET_MINIBATCH_K = 500


def determine_k(
    total_clients: int,
    *,
    min_clusters: int,
    max_clients_per_cluster: int,
    n_clusters: int | None = None,
) -> int:


    if total_clients <= 0:
        return 0

    min_k = min(max(1, min_clusters), total_clients)
    max_per = max(1, max_clients_per_cluster)
    k_for_max_size = int(ceil(total_clients / max_per))

    k = max(min_k, k_for_max_size)
    if n_clusters is not None:
        k = max(k, min(n_clusters, total_clients))

    return min(k, total_clients)


def _should_use_minibatch_kmeans(n: int, k: int) -> bool:


    return n >= LARGE_DATASET_MINIBATCH_N or k >= LARGE_DATASET_MINIBATCH_K


def _minibatch_size(n: int) -> int:









    return int(min(10_000, max(1_000, n // 100)))


def _fit_kmeans_sklearn(
    data: np.ndarray,
    k: int,
    *,
    max_iters: int,
    tol: float,
    seed: int,
) -> np.ndarray | None:


    try:
        from sklearn.cluster import KMeans, MiniBatchKMeans
    except ImportError:
        return None

    data_f32 = np.asarray(data, dtype=np.float32)
    n = len(data_f32)
    use_minibatch = _should_use_minibatch_kmeans(n, k)

    if use_minibatch:
        model = MiniBatchKMeans(
            n_clusters=k,
            init="k-means++",
            n_init=1,
            max_iter=max_iters,
            tol=tol,
            random_state=seed,
            batch_size=_minibatch_size(n),
        )
    else:
        model = KMeans(
            n_clusters=k,
            init="k-means++",
            n_init=1,
            max_iter=max_iters,
            tol=tol,
            random_state=seed,
            algorithm="elkan",
        )

    try:
        return model.fit_predict(data_f32)
    except MemoryError:
        if use_minibatch:
            return None
        model = MiniBatchKMeans(
            n_clusters=k,
            init="k-means++",
            n_init=1,
            max_iter=max_iters,
            tol=tol,
            random_state=seed,
            batch_size=_minibatch_size(n),
        )
        return model.fit_predict(data_f32)


def fit_kmeans(
    data: np.ndarray,
    k: int,
    *,
    max_iters: int = 100,
    tol: float = 1e-6,
    seed: int = 42,
) -> np.ndarray:


    n, _ = data.shape
    if n == 0:
        return np.array([], dtype=int)
    if k <= 1:
        return np.zeros(n, dtype=int)
    if k >= n:
        return np.arange(n, dtype=int)

    sklearn_labels = _fit_kmeans_sklearn(
        data, k, max_iters=max_iters, tol=tol, seed=seed
    )
    if sklearn_labels is not None:
        return np.asarray(sklearn_labels, dtype=int)

    rng = np.random.default_rng(seed)
    centroids = _kmeans_plus_plus_init(data, k, rng)
    labels = np.full(n, -1, dtype=int)

    for _ in range(max_iters):
        distances = _squared_distances(data, centroids)
        new_labels = np.argmin(distances, axis=1)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels

        new_centroids = centroids.copy()
        for cluster_idx in range(k):
            mask = labels == cluster_idx
            if not np.any(mask):
                new_centroids[cluster_idx] = data[rng.integers(n)]
            else:
                new_centroids[cluster_idx] = data[mask].mean(axis=0)

        if np.allclose(new_centroids, centroids, atol=tol, rtol=0):
            centroids = new_centroids
            break
        centroids = new_centroids

    return labels


def _split_oversized_cluster(
    labels: np.ndarray,
    data: np.ndarray,
    cluster_id: int,
    max_size: int,
    *,
    seed: int,
) -> np.ndarray:


    result = labels.copy()
    indexes = np.flatnonzero(result == cluster_id)
    if len(indexes) <= max_size:
        return result

    sub_k = int(ceil(len(indexes) / max_size))
    sub_labels = fit_kmeans(
        data[indexes],
        sub_k,
        max_iters=NESTED_KMEANS_MAX_ITERS,
        seed=seed + cluster_id,
    )
    if sub_k > 1 and len(set(int(label) for label in sub_labels)) <= 1:
        sub_labels = np.array([idx % sub_k for idx in range(len(indexes))], dtype=int)

    next_label = int(result.max()) + 1
    for sub_idx in range(sub_k):
        sub_indexes = indexes[sub_labels == sub_idx]
        if sub_idx == 0:
            result[sub_indexes] = cluster_id
        else:
            result[sub_indexes] = next_label
            next_label += 1
    return result


def _split_largest_for_min_count(
    labels: np.ndarray,
    data: np.ndarray,
    min_clusters: int,
    max_size: int,
    *,
    seed: int,
) -> np.ndarray:


    result = labels.copy()
    if _unique_cluster_count(result) >= min_clusters:
        return result

    cluster_id, indexes = _largest_cluster(result)
    if len(indexes) < 2:
        return result

    deficit = min_clusters - _unique_cluster_count(result)
    sub_k = min(len(indexes), max(2, deficit + 1))
    if max_size > 0:
        sub_k = max(sub_k, int(ceil(len(indexes) / max_size)))
    sub_k = min(sub_k, len(indexes))

    labels_before = _unique_cluster_count(result)
    sub_labels = fit_kmeans(
        data[indexes],
        sub_k,
        max_iters=NESTED_KMEANS_MAX_ITERS,
        seed=seed,
    )
    if sub_k > 1 and len(set(int(label) for label in sub_labels)) <= 1:
        sub_labels = np.array([idx % sub_k for idx in range(len(indexes))], dtype=int)

    next_label = int(result.max()) + 1
    for sub_idx in range(sub_k):
        sub_indexes = indexes[sub_labels == sub_idx]
        if len(sub_indexes) == 0:
            continue
        if sub_idx == 0:
            result[sub_indexes] = cluster_id
        else:
            result[sub_indexes] = next_label
            next_label += 1

    if _unique_cluster_count(result) <= labels_before:
        for idx in indexes[1:]:
            if _unique_cluster_count(result) >= min_clusters:
                break
            result[idx] = next_label
            next_label += 1
    return result


def enforce_clustering_constraints(
    labels: np.ndarray,
    data: np.ndarray,
    *,
    min_clusters: int,
    max_size: int,
    seed: int = 42,
) -> np.ndarray:


    if len(labels) == 0:
        return labels

    result = labels.copy()
    min_clusters = max(1, min_clusters)
    max_size = max(1, max_size)
    guard = 0
    max_guard = len(result) * 3

    while guard < max_guard:
        guard += 1
        oversized = _oversized_cluster_ids(result, max_size)
        if oversized:
            result = _split_oversized_cluster(
                result,
                data,
                oversized[0],
                max_size,
                seed=seed + guard,
            )
            continue
        if _unique_cluster_count(result) < min_clusters:
            result = _split_largest_for_min_count(
                result,
                data,
                min_clusters,
                max_size,
                seed=seed + guard,
            )
            continue
        break

    return result


def enforce_max_cluster_size(
    labels: np.ndarray,
    data: np.ndarray,
    max_size: int,
    *,
    seed: int = 42,
) -> np.ndarray:


    if max_size <= 0 or len(labels) == 0:
        return labels

    result = labels.copy()
    while True:
        oversized = _oversized_cluster_ids(result, max_size)
        if not oversized:
            break
        result = _split_oversized_cluster(
            result, data, oversized[0], max_size, seed=seed
        )
    return result


def enforce_min_cluster_count(
    labels: np.ndarray,
    data: np.ndarray,
    min_clusters: int,
    max_size: int,
    *,
    seed: int = 42,
) -> np.ndarray:


    if min_clusters <= 1 or len(labels) == 0:
        return labels

    result = labels.copy()
    guard = 0
    while _unique_cluster_count(result) < min_clusters and guard < len(result):
        guard += 1
        before = _unique_cluster_count(result)
        result = _split_largest_for_min_count(
            result, data, min_clusters, max_size, seed=seed + guard
        )
        if _unique_cluster_count(result) <= before:
            break
    return result


def relabel_contiguous(labels: np.ndarray) -> np.ndarray:


    if len(labels) == 0:
        return labels

    unique_labels = sorted(set(int(label) for label in labels))
    mapping = {old: new for new, old in enumerate(unique_labels)}
    return np.array([mapping[int(label)] for label in labels], dtype=int)


def _kmeans_plus_plus_init(data: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:











    n = len(data)
    centroids = np.empty((k, data.shape[1]), dtype=float)
    first_idx = int(rng.integers(n))
    centroids[0] = data[first_idx]

    closest_sq_dist = _squared_distances(data, centroids[:1]).reshape(-1)

    for centroid_idx in range(1, k):
        total = closest_sq_dist.sum()
        if total <= 0:
            centroids[centroid_idx] = data[int(rng.integers(n))]
        else:
            probabilities = closest_sq_dist / total
            chosen = int(rng.choice(n, p=probabilities))
            centroids[centroid_idx] = data[chosen]

        new_dist = _squared_distances(data, centroids[centroid_idx : centroid_idx + 1]).reshape(-1)
        closest_sq_dist = np.minimum(closest_sq_dist, new_dist)

    return centroids


def _squared_distances(data: np.ndarray, centroids: np.ndarray) -> np.ndarray:










    diff = data[:, np.newaxis, :] - centroids[np.newaxis, :, :]
    return np.sum(diff * diff, axis=2)


def _oversized_cluster_ids(labels: np.ndarray, max_size: int) -> list[int]:










    if len(labels) == 0:
        return []
    counts = np.bincount(labels.astype(np.int64))
    return [int(cluster_id) for cluster_id, count in enumerate(counts) if count > max_size]


def _unique_cluster_count(labels: np.ndarray) -> int:









    if len(labels) == 0:
        return 0
    return int(np.unique(labels).size)


def _largest_cluster(labels: np.ndarray) -> tuple[int, np.ndarray]:









    counts = np.bincount(labels.astype(np.int64))
    cluster_id = int(np.argmax(counts))
    indexes = np.flatnonzero(labels == cluster_id)
    return cluster_id, indexes


__all__ = [
    "MAIN_KMEANS_MAX_ITERS",
    "MAIN_KMEANS_TOL",
    "determine_k",
    "enforce_clustering_constraints",
    "enforce_max_cluster_size",
    "enforce_min_cluster_count",
    "fit_kmeans",
    "relabel_contiguous",
]
