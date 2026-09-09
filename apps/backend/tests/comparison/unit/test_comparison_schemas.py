

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from src.schema import (
    ComparisonDeltaItemSchema,
    ComparisonDeltaSchema,
    ComparisonRunsDataSchema,
    RunComparisonMetricsSchema,
    RunComparisonSnapshotSchema,
)


def _sample_parameters() -> dict:
    return {
        "id": 3,
        "utilization_rate": 0.7,
        "lgd": 0.8,
        "min_pd": 0.0,
        "max_pd": 1.0,
        "filter": True,
        "max_limit": 25000.0,
        "baseline_default_rate": 0.0553,
        "min_limit": 200.0,
        "discretize": True,
        "interchange": 0.0175,
        "max_rejected_limit": 25000.0,
        "enabled": True,
        "n_clusters": None,
        "max_clients_per_cluster": 500,
        "min_clusters": 100,
        "multipliers": [
            {
                "min_pd": "0.0000",
                "max_pd": "0.0500",
                "multiplier": "0.3000",
            }
        ],
        "created_at": datetime(2024, 10, 1, tzinfo=timezone.utc),
    }


def _sample_snapshot(run_id: int) -> dict:
    return {
        "run_id": run_id,
        "algorithm": "simplex",
        "status": "success",
        "created_at": datetime(2024, 10, 23, 14, 30, tzinfo=timezone.utc),
        "execution_time_ms": 12500,
        "csv_file_id": 7,
        "file_name": "clients_out2024.csv",
        "parameters": _sample_parameters(),
        "metrics": {
            "total_clients": 1500,
            "total_limit": 8_200_000.0,
            "total_income": 0.0,
            "total_loss": 0.0,
            "total_return": 24_700_000.0,
            "financial_default_rate": 0.068,
            "approval_rate": 0.78,
        },
        "limit_ranges": [
            {"range": "0-1k", "count": 5200, "percentage": 3.47},
            {"range": "1k-5k", "count": 14800, "percentage": 9.87},
        ],
        "return_by_cohort": [
            {
                "cohort_reference": "M3",
                "total_return": 10_200_000.0,
                "percentage": 41.3,
                "total_clients": 63500,
            }
        ],
        "cohort_analysis": [
            {
                "cohort": "M3",
                "client_count": 63500,
                "average_capacity": 11840.0,
                "average_limit": 9920.0,
                "approval_rate": 0.81,
            }
        ],
    }


def test_run_comparison_snapshot_schema_accepts_sample_payload():
    snapshot = RunComparisonSnapshotSchema(**_sample_snapshot(42))

    assert snapshot.run_id == 42
    assert snapshot.metrics.total_limit == 8_200_000.0
    assert snapshot.parameters.utilization_rate == 0.7
    assert len(snapshot.limit_ranges) == 2
    assert snapshot.return_by_cohort[0].percentage == 41.3


def test_comparison_runs_data_schema_roundtrip():
    payload = {
        "reference": _sample_snapshot(1),
        "compared": _sample_snapshot(2),
        "deltas": {
            "total_limit": {"absoluto": 600_000.0, "percentage": 7.89},
            "approval_rate": {"absoluto": 0.04, "percentage": 5.41},
            "total_return": {"absoluto": 3_400_000.0, "percentage": 15.96},
            "financial_default_rate": {"absoluto": -0.001, "percentage": -2.1},
            "total_clients": {"absoluto": 120.0, "percentage": 1.5},
        },
    }

    dto = ComparisonRunsDataSchema(**payload)
    dumped = dto.model_dump()

    assert dumped["reference"]["run_id"] == 1
    assert dumped["compared"]["run_id"] == 2
    assert dumped["deltas"]["total_return"]["percentage"] == 15.96


def test_comparison_delta_item_allows_null_percentage():
    delta = ComparisonDeltaItemSchema(absoluto=100.0, percentage=None)
    assert delta.percentage is None


def test_comparison_metrics_schema_requires_all_fields():
    with pytest.raises(Exception):
        RunComparisonMetricsSchema(total_clients=10)
