"""Schemas de request da API do backend."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .response import SchemaBase


class IngestionUploadRequestSchema(SchemaBase):


    filename: str
    source_type: Literal["file"] = "file"
    file_ref: str | None = None


class RunCreateSchema(SchemaBase):


    run_id: int
    algorithm: Literal["simplex", "simplex_ortools", "branch_bound"] = "simplex"
    client_tokens: list[str] = Field(default_factory=list)
    parameters_id: int | None = None


class OptimizationJobSchema(SchemaBase):









    run_id: int
    algorithm: Literal["simplex", "simplex_ortools", "branch_bound"] = "simplex"
    client_tokens: list[str] = Field(default_factory=list)
    parameters_id: int | None = None
    enabled: bool | None = None
    n_clusters: int | None = None
    max_clients_per_cluster: int | None = Field(default=None, ge=1)
    min_clusters: int | None = Field(default=None, ge=100)


class ParametersUpdateRequestSchema(SchemaBase):


    utilization_rate: float | None = None
    lgd: float | None = None
    min_pd: float | None = None
    max_pd: float | None = None
    filter: bool | None = None
    max_limit: float | None = None
    baseline_default_rate: float | None = None
    min_limit: float | None = None
    discretize: bool | None = None
    interchange: float | None = None
    max_rejected_limit: float | None = None
    enabled: bool | None = None
    n_clusters: int | None = None
    max_clients_per_cluster: int | None = Field(default=None, ge=1)
    min_clusters: int | None = Field(default=None, ge=100)
    multipliers: list[dict[str, str | float]] | None = None


class StatisticsDashboardRequestSchema(SchemaBase):


    csv_file_id: int | None = None
    run_id: int | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    sort_by: str | None = None
    sort_order: Literal["asc", "desc"] | None = None
