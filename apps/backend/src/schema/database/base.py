"""Declarative base shared by the schema's ORM models."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy models."""

    pass

__all__ = ["Base"]
