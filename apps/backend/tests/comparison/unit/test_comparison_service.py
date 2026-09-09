"""Tests do comparison_service (snapshot)."""

from __future__ import annotations

import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import src.utils.db.session as db_session
from src.schema import RunComparisonSnapshotSchema
from src.schema.database.base import Base
from src.utils.db.session import get_db_session


@pytest.fixture()
def in_memory_db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    db_session.SessionLocal = SessionLocal
    yield


def _seed_run_with_context(
    *,
    with_result: bool = True,
    status: str = "success",
    total_limit: float = 5000.0,
    total_return: float = 200.0,
    file_name: str = "clients.csv",
) -> int:
    from src.repositories import (
        CsvFileRepository,
        ClientRepository,
        ParametersRepository,
        ResultRepository,
        RunRepository,
    )
    from src.schema.database.portfolio_results import PortfolioResults

    with get_db_session() as session:
        file = CsvFileRepository(session).create(
            CsvFileRepository(session).model(
                name=file_name,
                path_or_url=f"minio://test/{file_name}",
            )
        )

        params = ParametersRepository(session).create(
            ParametersRepository(session).model(
                utilization_rate=0.7,
                lgd=0.8,
                min_pd=0.0,
                max_pd=1.0,
                filter=False,
                max_limit=25000.0,
                baseline_default_rate=0.05,
                min_limit=200.0,
                discretize=False,
                interchange=0.0175,
                max_rejected_limit=25000.0,
                enabled=True,
                n_clusters=None,
                max_clients_per_cluster=500,
                min_clusters=100,
                multipliers=[],
            )
        )

        run = RunRepository(session).create(
            RunRepository(session).model(
                algorithm="simplex",
                execution_time_ms=1200,
                status=status,
                parameters_id=params.id,
                csv_file_id=file.id,
            )
        )

        if with_result:
            ResultRepository(session).create(
                PortfolioResults(
                    run_id=run.id,
                    total_clients=2,
                    total_limit=total_limit,
                    total_income=100.0,
                    total_loss=50.0,
                    total_return=total_return,
                    financial_default_rate=0.05,
                    baseline_default_rate=0.04,
                )
            )

        ClientRepository(session).create(
            ClientRepository(session).model(
                token=f"run{run.id}_c1",
                last_run_id=run.id,
                last_suggested_limit=2500.0,
                payment_capacity=3000.0,
                score=0.8,
                pd=0.10,
            )
        )
        ClientRepository(session).create(
            ClientRepository(session).model(
                token=f"run{run.id}_c2",
                last_run_id=run.id,
                last_suggested_limit=0.0,
                payment_capacity=2800.0,
                score=0.7,
                pd=0.20,
            )
        )

        return run.id


def test_get_run_snapshot_returns_valid_payload(in_memory_db):
    from src.services.comparison_service import get_run_snapshot

    run_id = _seed_run_with_context()
    snapshot = get_run_snapshot(run_id)

    dto = RunComparisonSnapshotSchema(**snapshot)
    assert dto.run_id == run_id
    assert dto.algorithm == "simplex"
    assert dto.file_name == "clients.csv"
    assert dto.parameters.utilization_rate == 0.7
    assert dto.metrics.total_limit == 5000.0
    assert dto.metrics.total_return == 200.0
    assert dto.metrics.approval_rate == 0.5
    assert dto.metrics.financial_default_rate == pytest.approx(0.05)
    assert dto.return_by_cohort == []
    assert dto.cohort_analysis == []
    assert len(dto.limit_ranges) == 6


def test_get_run_snapshot_raises_for_missing_run(in_memory_db):
    from src.services.comparison_service import (
        RunNotFoundForComparisonError,
        get_run_snapshot,
    )

    with pytest.raises(RunNotFoundForComparisonError, match="not found"):
        get_run_snapshot(999)


def test_get_run_snapshot_raises_without_result(in_memory_db):
    from src.services.comparison_service import (
        RunNotComparableError,
        get_run_snapshot,
    )

    run_id = _seed_run_with_context(with_result=False)

    with pytest.raises(RunNotComparableError, match="has no result"):
        get_run_snapshot(run_id)


def test_get_run_snapshot_includes_cohort_data_from_clusters(in_memory_db):
    from src.services.comparison_service import get_run_snapshot
    from tests.comparison.conftest import seed_run_clusters

    run_id = _seed_run_with_context(total_return=300.0)
    seed_run_clusters(run_id)

    snapshot = get_run_snapshot(run_id)

    assert len(snapshot["cohort_analysis"]) == 2
    assert snapshot["cohort_analysis"][0]["cohort"] == "Cluster 1"
    assert snapshot["return_grouping"] == "cluster"
    assert len(snapshot["return_by_cohort"]) == 2
    assert snapshot["return_by_cohort"][0]["percentage"] == pytest.approx(66.67, rel=1e-2)


def test_get_run_snapshot_uses_clients_cohort_ref_when_no_clusters(in_memory_db):
    from src.repositories import ClientRepository, ComparisonRepository
    from src.services.comparison_service import get_run_snapshot

    run_id = _seed_run_with_context(total_return=300.0)

    with get_db_session() as session:
        clients = ComparisonRepository(session).get_clients_by_run(run_id)
        repo = ClientRepository(session)
        for client, cohort in zip(clients, ("M1", "M2")):
            repo.update_by_id(client.id, {"cohort_reference": cohort})

    snapshot = get_run_snapshot(run_id)

    assert len(snapshot["cohort_analysis"]) == 2
    assert {row["cohort"] for row in snapshot["cohort_analysis"]} == {"M1", "M2"}
    assert snapshot["return_grouping"] == "cohort"


def test_build_summary_maps_domain_fields(in_memory_db):
    from src.repositories import ComparisonRepository
    from src.services.comparison_service import _build_summary

    run_id = _seed_run_with_context()

    with get_db_session() as session:
        repo = ComparisonRepository(session)
        run = repo.get_run_with_context(run_id)
        clients = repo.get_clients_by_run(run_id)
        summary = _build_summary(run, run.result, clients)

    assert summary.run_id == run_id
    assert summary.total_clients == 2
    assert float(summary.total_limit) == 5000.0
    assert float(summary.approval_rate) == 0.5
    assert float(summary.financial_default_rate) == pytest.approx(0.05)
    assert summary.file_name == "clients.csv"


def test_compare_runs_returns_snapshots_and_deltas(in_memory_db):
    from src.schema import ComparisonRunsDataSchema
    from src.services.comparison_service import compare_runs

    ref_id = _seed_run_with_context(total_limit=5000.0, total_return=200.0)
    cmp_id = _seed_run_with_context(
        total_limit=6000.0,
        total_return=300.0,
        file_name="clients_b.csv",
    )

    payload = compare_runs(ref_id, cmp_id)
    dto = ComparisonRunsDataSchema(**payload)

    assert dto.reference.run_id == ref_id
    assert dto.compared.run_id == cmp_id
    assert dto.deltas.total_limit.absoluto == 1000.0
    assert dto.deltas.total_limit.percentage == pytest.approx(20.0)
    assert dto.deltas.total_return.absoluto == 100.0
    assert dto.deltas.total_return.percentage == pytest.approx(50.0)


def test_compare_runs_rejects_same_run_id(in_memory_db):
    from src.services.comparison_service import (
        SameRunComparisonError,
        compare_runs,
    )

    run_id = _seed_run_with_context()

    with pytest.raises(SameRunComparisonError):
        compare_runs(run_id, run_id)


def test_compare_runs_raises_for_missing_run(in_memory_db):
    from src.services.comparison_service import (
        RunNotFoundForComparisonError,
        compare_runs,
    )

    run_id = _seed_run_with_context()

    with pytest.raises(RunNotFoundForComparisonError):
        compare_runs(run_id, 999)


def test_compare_runs_raises_for_run_without_result(in_memory_db):
    from src.services.comparison_service import (
        RunNotComparableError,
        compare_runs,
    )

    ref_id = _seed_run_with_context()
    cmp_id = _seed_run_with_context(with_result=False)

    with pytest.raises(RunNotComparableError, match="has no result"):
        compare_runs(ref_id, cmp_id)


def test_compare_runs_raises_for_non_success_status(in_memory_db):
    from src.services.comparison_service import (
        RunNotComparableError,
        compare_runs,
    )

    ref_id = _seed_run_with_context()
    cmp_id = _seed_run_with_context(status="error")

    with pytest.raises(RunNotComparableError, match="did not complete successfully"):
        compare_runs(ref_id, cmp_id)


def test_get_run_snapshot_uses_audit_when_last_run_id_overwritten(in_memory_db):

    from src.repositories import (
        CsvFileRepository,
        ClientRepository,
        ClientHistoryRepository,
        ParametersRepository,
        ResultRepository,
        RunRepository,
    )
    from src.schema.database.portfolio_results import PortfolioResults
    from src.services.comparison_service import get_run_snapshot
    from src.custom_types import ClientChangeType

    shared_token = "shared_client"

    with get_db_session() as session:
        file = CsvFileRepository(session).create(
            CsvFileRepository(session).model(
                name="clients.csv",
                path_or_url="minio://test/clients.csv",
            )
        )
        params = ParametersRepository(session).create(
            ParametersRepository(session).model(
                utilization_rate=0.7,
                lgd=0.8,
                min_pd=0.0,
                max_pd=1.0,
                filter=False,
                max_limit=25000.0,
                baseline_default_rate=0.05,
                min_limit=200.0,
                discretize=False,
                interchange=0.0175,
                max_rejected_limit=25000.0,
                enabled=True,
                n_clusters=None,
                max_clients_per_cluster=500,
                min_clusters=100,
                multipliers=[],
            )
        )

        run_repo = RunRepository(session)
        result_repo = ResultRepository(session)
        history_repo = ClientHistoryRepository(session)
        client_repo = ClientRepository(session)

        older_run = run_repo.create(
            run_repo.model(
                algorithm="simplex",
                execution_time_ms=1200,
                status="success",
                parameters_id=params.id,
                csv_file_id=file.id,
            )
        )
        newer_run = run_repo.create(
            run_repo.model(
                algorithm="simplex",
                execution_time_ms=1300,
                status="success",
                parameters_id=params.id,
                csv_file_id=file.id,
            )
        )

        for run, total_limit, approved in (
            (older_run, 2500.0, 1),
            (newer_run, 0.0, 0),
        ):
            result_repo.create(
                PortfolioResults(
                    run_id=run.id,
                    total_clients=1,
                    total_limit=total_limit,
                    total_income=100.0,
                    total_loss=50.0,
                    total_return=100.0,
                    financial_default_rate=0.05,
                    baseline_default_rate=0.04,
                    approved=approved,
                    approval_rate=approved,
                )
            )

        client_repo.create(
            client_repo.model(
                token=shared_token,
                last_run_id=newer_run.id,
                last_suggested_limit=0.0,
                payment_capacity=3000.0,
                score=0.8,
                pd=0.10,
            )
        )

        history_repo.register_change(
            shared_token,
            ClientChangeType.NEW_CLIENT,
            current_state={
                "run_id": older_run.id,
                "suggested_limit": 2500.0,
                "payment_capacity": 3000.0,
                "score": 0.8,
                "pd": 0.10,
            },
            run_id=older_run.id,
        )
        history_repo.register_change(
            shared_token,
            ClientChangeType.LIMIT_UPDATED,
            current_state={
                "run_id": newer_run.id,
                "suggested_limit": 0.0,
                "payment_capacity": 3000.0,
                "score": 0.8,
                "pd": 0.10,
            },
            previous_state={
                "run_id": older_run.id,
                "suggested_limit": 2500.0,
            },
            run_id=newer_run.id,
        )

        older_run_id = older_run.id
        newer_run_id = newer_run.id

    older_snapshot = get_run_snapshot(older_run_id)
    newer_snapshot = get_run_snapshot(newer_run_id)

    assert older_snapshot["metrics"]["approval_rate"] == 1.0
    assert newer_snapshot["metrics"]["approval_rate"] == 0.0
    assert sum(bucket["count"] for bucket in older_snapshot["limit_ranges"]) == 1
    assert sum(bucket["count"] for bucket in newer_snapshot["limit_ranges"]) == 1
