"""ORM model for consolidated portfolio results."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.schema.database.base import Base

if TYPE_CHECKING:
    from src.schema.database.run import Run


class PortfolioResults(Base):


    __tablename__ = "results"
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_results_run_id"),
        Index("idx_results_run_id", "run_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("run.id"), nullable=False)
    total_clients: Mapped[int] = mapped_column(Integer, nullable=False)
    total_limit: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_income: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_loss: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_return: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    financial_default_rate: Mapped[Decimal] = mapped_column(
        Numeric(6, 4), nullable=False
    )
    baseline_default_rate: Mapped[Decimal] = mapped_column(
        Numeric(6, 4), nullable=False
    )
    # Stored at run-completion time so historical queries remain correct even after
    # clients are re-processed by subsequent runs (last_run_id gets overwritten).
    approved: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approval_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 6), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    run: Mapped["Run"] = relationship("Run", back_populates="result")


__all__ = ["PortfolioResults"]
