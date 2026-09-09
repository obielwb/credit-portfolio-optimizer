

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.schema.database.base import Base

if TYPE_CHECKING:
    from src.schema.database.run import Run


class RunClusters(Base):


    __tablename__ = "run_clusters"
    __table_args__ = (
        Index("idx_run_clusters_run_id", "run_id"),
        Index("idx_run_clusters_cluster_id", "cluster_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("run.id"), nullable=False)
    cluster_id: Mapped[int] = mapped_column(Integer, nullable=False)
    total_clients: Mapped[int] = mapped_column(Integer, nullable=False)
    average_pd: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    average_score: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    average_capacity: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    policy_name: Mapped[str] = mapped_column(String(100), nullable=True)
    leverage_multiplier: Mapped[float] = mapped_column(Numeric(6, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    run: Mapped["Run"] = relationship("Run", back_populates="clusters")


__all__ = ["RunClusters"]
