"""ORM model for algorithm runs."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.schema.database.base import Base

if TYPE_CHECKING:
    from src.schema.database.csv_file import CsvFile
    from src.schema.database.client import Client
    from src.schema.database.parameters import Parameters
    from src.schema.database.portfolio_results import PortfolioResults


class Run(Base):
    """Individual algorithm run."""

    __tablename__ = "run"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'success', 'error', 'timeout')",
            name="status_valido",
        ),
        Index("idx_run_algorithm", "algorithm"),
        Index("idx_run_created_at", "created_at", postgresql_ops={"created_at": "DESC"}),
        Index("idx_run_parameters_id", "parameters_id"),
        Index("idx_run_csv_file_id", "csv_file_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False)
    execution_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    state_operacional: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="waiting_for_processing"
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    parameters_id: Mapped[int] = mapped_column(
        ForeignKey("parameters.id"), nullable=False
    )
    csv_file_id: Mapped[int] = mapped_column(
        ForeignKey("files_csv.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    parameters: Mapped["Parameters"] = relationship("Parameters", back_populates="runs")
    file_csv: Mapped["CsvFile"] = relationship(
        "CsvFile", back_populates="runs"
    )
    result: Mapped["PortfolioResults | None"] = relationship(
        "PortfolioResults", back_populates="run", uselist=False
    )
    clients: Mapped[list["Client"]] = relationship(
        "Client", back_populates="last_run"
    )
    clusters: Mapped[list["RunClusters"]] = relationship(
        "RunClusters", back_populates="run"
    )


__all__ = ["Run"]
