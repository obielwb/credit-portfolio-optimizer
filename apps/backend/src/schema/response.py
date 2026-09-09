"""Schemas de response da API do backend."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SchemaBase(BaseModel):


    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class HealthDataSchema(SchemaBase):
    """Common data returned by health endpoints."""

    service: str
    version: str
    timestamp: datetime
    uptime: str | None = None
    database: Literal["ok", "unknown", "error"] | None = None
    queue: Literal["ok", "unknown", "error"] | None = None
    storage: Literal["ok", "unknown", "error"] | None = None
    dependencies: list[Literal["ok", "unknown", "error"]] | None = None
    process: Literal["alive", "dead"] | None = None


class HealthResponseSchema(SchemaBase):


    status: Literal["ok", "unknown", "error"]
    data: HealthDataSchema


class IngestionUploadResponseSchema(SchemaBase):


    run_id: int
    filename: str
    algorithm: Literal["simplex", "simplex_ortools", "branch_bound"] = "simplex"
    state: Literal["queued", "csv_ingestion", "completed", "failed"] = "queued"
    accepted_formats: list[str] = Field(
        default_factory=lambda: ["csv", "parquet", "pq"]
    )


class RunStatusSchema(SchemaBase):


    run_id: int
    state: Literal[
        "waiting_for_processing",
        "ingestion",
        "calculating_constraints",
        "tableau_calculation",
        "generating_recommendations",
        "validating_constraints",
        "completed",
        "failed",
    ]
    current_stage: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None


class RunResultSchema(SchemaBase):


    run_id: int
    final_status: Literal["success", "error", "timeout"]
    algorithm: Literal["simplex", "simplex_ortools", "branch_bound"]
    result_id: int | None = None
    error: str | None = None
    released_at: datetime | None = None


class ParametersSchema(SchemaBase):
    """Currently active parameters and historical versions."""

    id: int
    utilization_rate: float
    lgd: float
    min_pd: float
    max_pd: float
    filter: bool
    max_limit: float
    baseline_default_rate: float
    min_limit: float
    discretize: bool
    interchange: float
    max_rejected_limit: float
    enabled: bool
    n_clusters: int | None = None
    max_clients_per_cluster: int
    min_clusters: int
    multipliers: list[dict[str, str | float]]
    created_at: datetime


class FileSchema(SchemaBase):


    csv_file_id: int
    file_name: str
    created_at: datetime | None = None
    run_id: int | None = None


class DashboardClientSchema(SchemaBase):


    token: str
    payment_capacity: float
    score: float
    suggested_limit: float | None = None
    pd: float


class ClientResultSchema(SchemaBase):


    token: str
    payment_capacity: float
    propensity_score: float
    pd: float
    suggested_limit: float
    expected_income: float
    expected_loss: float
    expected_return: float


class DashboardTotalsSchema(SchemaBase):
    """Totais consolidated exibidos na home."""

    total_clients: int
    total_suggested_limit: float
    approval_rate: float
    expected_return: float


class StatisticsDashboardSchema(SchemaBase):
    """Resposta principal do endpoint de dashboard."""

    file: FileSchema
    clients: list[DashboardClientSchema]
    totais: DashboardTotalsSchema
    pagina: int
    page_size: int
    total_items: int
    total_pages: int
    sort_by: str | None = None
    sort_order: Literal["asc", "desc"] | None = None


class StatisticsRunSchema(SchemaBase):


    total_runs: int
    completed_runs: int
    failed_runs: int
    avg_duration_ms: int


class StatisticsPortfolioSchema(SchemaBase):
    """Aggregate metrics for the optimized portfolio."""

    total_limit: float
    total_income: float
    total_loss: float
    total_return: float
    financial_default_rate: float
    baseline_default_rate: float
    total_clients: int
    approval_rate: float


class StatisticsPortfolioResponseSchema(SchemaBase):


    portfolio: StatisticsPortfolioSchema
    limit_ranges: list[LimitsBucketSchema]
    return_by_cohort: list[ReturnByCohortSchema]


class StatisticsClientResultsSchema(SchemaBase):


    file: FileSchema
    items: list[ClientResultSchema]
    total_items: int


class LimitsBucketSchema(SchemaBase):


    range: str
    count: int
    percentage: float


class ExecutionHistoryItemSchema(SchemaBase):
    """Run-history row."""

    run_id: int
    algorithm: str
    status: Literal["success", "error", "timeout", "pending"]
    csv_file_id: int
    file_name: str
    total_clients: int
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    execution_time_ms: int | None = None
    approved: int | None = None
    error_reason: str | None = None
    total_limit: float | None = None
    approval_rate: float | None = None
    total_return: float | None = None


class ExecutionLogEntrySchema(SchemaBase):


    t: str
    tipo: Literal["info", "ok", "warn", "error"]
    msg: str


class LimitDistributionSchema(SchemaBase):
    """Distribution of suggested limits versus capacity."""

    above: int
    full: int
    denied: int


class ExecutionDetailSchema(SchemaBase):


    run_id: int
    algorithm: str
    status: Literal["success", "error", "timeout", "pending"]
    csv_file_id: int
    file_name: str
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    execution_time_ms: int | None = None
    total_clients: int = 0
    approved: int = 0
    approval_rate: float | None = None
    average_approved_score: float | None = None
    total_limit: float | None = None
    total_return: float | None = None
    error_reason: str | None = None
    parameters: ParametersSchema | None = None
    distribution: LimitDistributionSchema | None = None
    limit_ranges: list[LimitsBucketSchema] = Field(default_factory=list)
    operational_log: list[ExecutionLogEntrySchema] = Field(default_factory=list)
    download_csv_url: str | None = None


class ExecutionHistorySchema(SchemaBase):
    """Run-history response."""

    items: list[ExecutionHistoryItemSchema]
    total_items: int


class ReturnByCohortSchema(SchemaBase):


    cohort_reference: str
    total_clients: int
    total_return: float


class CohortAnalysisSchema(SchemaBase):


    cohort: str
    client_count: int
    average_capacity: float
    average_limit: float
    approval_rate: float


class ComparisonReturnByCohortSchema(SchemaBase):


    cohort_reference: str
    total_return: float
    percentage: float
    total_clients: int | None = None


class RunComparisonMetricsSchema(SchemaBase):


    total_clients: int
    total_limit: float
    total_income: float
    total_loss: float
    total_return: float
    financial_default_rate: float
    approval_rate: float


class RunComparisonSnapshotSchema(SchemaBase):


    run_id: int
    algorithm: str
    status: Literal["success", "error", "timeout", "pending"]
    created_at: datetime
    execution_time_ms: int | None = None
    csv_file_id: int
    file_name: str
    parameters: ParametersSchema
    metrics: RunComparisonMetricsSchema
    limit_ranges: list[LimitsBucketSchema]
    return_by_cohort: list[ComparisonReturnByCohortSchema] = Field(
        default_factory=list
    )
    cohort_analysis: list[CohortAnalysisSchema] = Field(default_factory=list)
    return_grouping: Literal["cohort", "cluster"] = "cohort"


class ComparisonDeltaItemSchema(SchemaBase):
    """Absolute and percentage delta between two metrics."""

    absoluto: float
    percentage: float | None = None


class ComparisonDeltaSchema(SchemaBase):
    """Deltas between the compared and reference runs."""

    total_limit: ComparisonDeltaItemSchema
    approval_rate: ComparisonDeltaItemSchema
    total_return: ComparisonDeltaItemSchema
    financial_default_rate: ComparisonDeltaItemSchema
    total_clients: ComparisonDeltaItemSchema
    total_income: ComparisonDeltaItemSchema | None = None
    total_loss: ComparisonDeltaItemSchema | None = None


class ComparisonRunsDataSchema(SchemaBase):
    """Payload for comparing two runs."""

    reference: RunComparisonSnapshotSchema
    compared: RunComparisonSnapshotSchema
    deltas: ComparisonDeltaSchema


class StatisticsReportSchema(SchemaBase):
    """PDF report export response."""

    report_id: str
    download_url: str
    generated_at: datetime
    csv_file_id: int | None = None
    run_id: int | None = None


class SuccessResponseSchema(SchemaBase):
    """Default API success envelope."""

    status: Literal["ok"] = "ok"
    data: dict[str, object]
    meta: dict[str, object] = Field(default_factory=dict)


class ErrorResponseSchema(SchemaBase):
    """Default API error envelope."""

    status: Literal["error"] = "error"
    code: str
    message: str
    details: dict[str, object] = Field(default_factory=dict)


PortfolioSummaryBaseSchema = StatisticsPortfolioSchema
DashboardFileSchema = FileSchema
