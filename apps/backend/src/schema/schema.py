

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SchemaBase(BaseModel):


    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RunCreateSchema(SchemaBase):


    run_id: int
    algorithm: Literal["simplex", "simplex_ortools", "branch_bound"] = "simplex"
    parameters_id: int | None = None


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
    status: Literal["success", "error", "timeout"]
    state: Literal["completed", "failed"]
    algorithm: Literal["simplex", "simplex_ortools", "branch_bound"]
    result_id: int | None = None
    error: str | None = None
    released_at: datetime | None = None
