"""ORM model for algorithm parameters."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, Numeric, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.schema.database.base import Base

if TYPE_CHECKING:
    from src.schema.database.run import Run

json_type = JSON().with_variant(JSONB, "postgresql")


class Parameters(Base):


    __tablename__ = "parameters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    utilization_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    lgd: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    min_pd: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    max_pd: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    filter: Mapped[bool] = mapped_column(Boolean, nullable=False)
    max_limit: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    baseline_default_rate: Mapped[Decimal] = mapped_column(
        Numeric(6, 4), nullable=False
    )
    min_limit: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discretize: Mapped[bool] = mapped_column(Boolean, nullable=False)
    interchange: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    max_rejected_limit: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    n_clusters: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_clients_per_cluster: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1000
    )
    min_clusters: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100
    )
    multipliers: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    runs: Mapped[list["Run"]] = relationship(
        "Run", back_populates="parameters", cascade="all, delete-orphan"
    )


__all__ = ["Parameters"]
