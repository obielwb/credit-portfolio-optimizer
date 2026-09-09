

from __future__ import annotations

from pathlib import Path

from .contracts import ClusteringInput, SimplexClusterSummary
from .service import clusterize, summarize_for_simplex
from .models import ClusteringResult


def run_clustering(payload: ClusteringInput) -> ClusteringResult:


    return clusterize(payload)


def prepare_summary_for_simplex(payload: ClusteringInput) -> list[SimplexClusterSummary]:


    result = run_clustering(payload)
    return summarize_for_simplex(result)


__all__ = ["run_clustering", "prepare_summary_for_simplex"]