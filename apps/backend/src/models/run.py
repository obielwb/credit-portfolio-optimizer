

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime

from src.models.csv_file import CsvFile
from src.models.parameters import OptimizationParameters
from src.models.result import PortfolioResult


class RunStatus(str, enum.Enum):


    PENDING = "pending"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class RunState(str, enum.Enum):
    """Real-time run progress state for frontend polling."""

    WAITING_FOR_PROCESSING = "waiting_for_processing"
    INGESTION = "ingestion"
    CALCULATING_CONSTRAINTS = "calculating_constraints"
    TABLEAU_CALCULATION = "tableau_calculation"
    GENERATING_RECOMMENDATIONS = "generating_recommendations"
    VALIDATING_CONSTRAINTS = "validating_constraints"
    COMPLETED = "completed"
    FAILED = "failed"


ETAPA_LABELS: dict[RunState, str] = {
    RunState.WAITING_FOR_PROCESSING: "Waiting processamento",
    RunState.INGESTION: "Data ingestion",
    RunState.CALCULATING_CONSTRAINTS: "Applying parameters",
    RunState.TABLEAU_CALCULATION: "Calculating optimization matrix",
    RunState.GENERATING_RECOMMENDATIONS: "Generating limit recommendations",
    RunState.VALIDATING_CONSTRAINTS: "Validating business constraints",
    RunState.COMPLETED: "Completed",
    RunState.FAILED: "Failed",
}


@dataclass(frozen=True, slots=True)
class OptimizationRun:
    """Complete run from ingestion through result release."""

    state: RunState
    status: RunStatus
    algorithm: str
    parameters: OptimizationParameters
    file_csv: CsvFile
    result: PortfolioResult | None = None
    error: str | None = None
    execution_time_ms: int | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


__all__ = [
    "RunState",
    "ETAPA_LABELS",
    "OptimizationRun",
    "RunStatus",
]
