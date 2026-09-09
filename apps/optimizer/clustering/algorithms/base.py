

from __future__ import annotations

from typing import Protocol

from ..contracts import ClusteringInput
from ..models import ClusteringResult


class ClusterAlgorithm(Protocol):
    """Contract implemented by clustering strategies."""

    name: str
    version: str

    def execute(self, payload: ClusteringInput) -> ClusteringResult:
        """Cluster the provided client feature matrix."""

        ...
