

from .base import ClusterAlgorithm
from .kmeans import KMeansClusterAlgorithm


STRATEGY_REGISTRY: dict[str, type] = {
    "kmeans": KMeansClusterAlgorithm,
    "balanced": KMeansClusterAlgorithm,
}


__all__ = ["ClusterAlgorithm", "KMeansClusterAlgorithm", "STRATEGY_REGISTRY"]
