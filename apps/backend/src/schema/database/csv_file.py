"""ORM model for input CSV files."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.schema.database.base import Base

if TYPE_CHECKING:
    from src.schema.database.run import Run


class CsvFile(Base):


    __tablename__ = "files_csv"
    __table_args__ = (
        Index("idx_files_csv_name", "name"),
        Index("idx_files_csv_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path_or_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    runs: Mapped[list["Run"]] = relationship("Run", back_populates="file_csv")


__all__ = ["CsvFile"]
