import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from clustering.algorithms.kmeans_core import (
    determine_k,
    enforce_clustering_constraints,
    enforce_max_cluster_size,
    enforce_min_cluster_count,
    fit_kmeans,
)


def test_determine_k_respects_min_clusters():
    assert determine_k(500, min_clusters=100, max_clients_per_cluster=1000) == 100


def test_fit_kmeans_assigns_all_points():
    data = np.array(
        [
            [0.0, 0.0],
            [0.1, 0.0],
            [10.0, 10.0],
            [10.1, 10.0],
        ],
        dtype=float,
    )
    labels = fit_kmeans(data, k=2, seed=1)

    assert len(labels) == 4
    assert set(labels) <= {0, 1}
    assert labels[0] == labels[1]
    assert labels[2] == labels[3]
    assert labels[0] != labels[2]


def test_enforce_max_cluster_size_splits_large_cluster():
    data = np.array([[float(i), float(i)] for i in range(6)], dtype=float)
    labels = np.zeros(6, dtype=int)

    adjusted = enforce_max_cluster_size(labels, data, max_size=2, seed=7)

    assert len(adjusted) == 6
    counts = np.bincount(adjusted)
    assert all(count <= 2 for count in counts)


def test_enforce_clustering_constraints_respects_max_and_min():
    data = np.array([[float(i), float(i)] for i in range(12)], dtype=float)
    labels = np.zeros(12, dtype=int)

    adjusted = enforce_clustering_constraints(
        labels,
        data,
        min_clusters=4,
        max_size=3,
        seed=11,
    )

    counts = np.bincount(adjusted)
    assert len(counts) >= 4
    assert all(count <= 3 for count in counts)


def test_enforce_min_cluster_count_splits_largest_cluster():
    data = np.array([[float(i), 0.0] for i in range(10)], dtype=float)
    labels = np.zeros(10, dtype=int)

    adjusted = enforce_min_cluster_count(labels, data, min_clusters=4, max_size=10, seed=3)

    assert len(set(int(label) for label in adjusted)) == 4
