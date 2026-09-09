

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CsvFile:
    """Reference to a CSV file stored in an object bucket."""

    name: str
    path_or_url: str
    id: int | None = None
    created_at: datetime | None = None


__all__ = ["CsvFile"]
