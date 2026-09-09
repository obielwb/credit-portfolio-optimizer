"""ORM model for the client table."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.schema.database.base import Base

if TYPE_CHECKING:
    from src.schema.database.run import Run


class Client(Base):
    """Client and the algorithm's latest suggested limit."""

    __tablename__ = "clients"
    __table_args__ = (
        UniqueConstraint("token", name="uq_clients_token"),
        Index("idx_clients_token", "token"),
        Index("idx_clients_last_run_id", "last_run_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(100), nullable=False)
    last_run_id: Mapped[int] = mapped_column(ForeignKey("run.id"), nullable=False)
    last_suggested_limit: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    payment_capacity: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    score: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    pd: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    filter_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cohort_reference: Mapped[str | None] = mapped_column(String(10), nullable=True)

    last_run: Mapped["Run"] = relationship("Run", back_populates="clients")


__all__ = ["Client"]
