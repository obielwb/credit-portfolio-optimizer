"""ORM model for the client audit table."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.schema.database.base import Base
from src.custom_types import ClientChangeType

json_type = JSON().with_variant(JSONB, "postgresql")

_change_type_values = [item.value for item in ClientChangeType]
pg_change_type_enum = PG_ENUM(
    *_change_type_values,
    name="change_type_enum",
    create_type=False,
)
sqlite_change_type_enum = Enum(
    ClientChangeType,
    values_callable=lambda enum_class: [item.value for item in enum_class],
)
change_type_enum_type = pg_change_type_enum.with_variant(
    sqlite_change_type_enum,
    "sqlite",
)


class ClientHistory(Base):


    __tablename__ = "audit_clients"
    __table_args__ = (
        Index("idx_audit_clients_token", "token"),
        Index(
            "idx_audit_clients_created_at",
            "created_at",
            postgresql_ops={"created_at": "DESC"},
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(100), nullable=False)
    change_type: Mapped[ClientChangeType] = mapped_column(
        change_type_enum_type,
        nullable=False,
    )
    previous_state: Mapped[dict[str, Any] | None] = mapped_column(json_type)
    current_state: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)

    run_id: Mapped[int | None] = mapped_column(ForeignKey("run.id"), nullable=True)
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


__all__ = ["ClientHistory", "pg_change_type_enum"]
