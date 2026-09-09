

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class RunResultSummary:


    run_id: int
    algorithm: str
    created_at: datetime | None
    total_clients: int
    total_limit: Decimal
    total_income: Decimal
    total_loss: Decimal
    total_return: Decimal
    financial_default_rate: Decimal
    approval_rate: Decimal
    csv_file_id: int | None = None
    file_name: str | None = None


@dataclass(frozen=True, slots=True)
class DeltaRunResult:


    run_id: int
    run_reference_id: int
    total_limit: Decimal
    total_income: Decimal
    total_loss: Decimal
    total_return: Decimal
    financial_default_rate: Decimal
    approval_rate: Decimal


@dataclass(frozen=True, slots=True)
class ComparisonRuns:
    """Compare results using the first run as the reference."""
    reference: RunResultSummary
    compared: RunResultSummary



    @property
    def deltas(self) -> list[DeltaRunResult]:






        run = self.compared
        delta = DeltaRunResult(
            run_id=run.run_id,
            run_reference_id=self.reference.run_id,
            total_limit=run.total_limit - self.reference.total_limit,
            total_income=run.total_income - self.reference.total_income,
            total_loss=run.total_loss - self.reference.total_loss,
            total_return=run.total_return - self.reference.total_return,
            financial_default_rate=(
                run.financial_default_rate - self.reference.financial_default_rate
            ),
            approval_rate=run.approval_rate - self.reference.approval_rate,
        )
        return [delta]


__all__ = ["ComparisonRuns", "DeltaRunResult", "RunResultSummary"]
