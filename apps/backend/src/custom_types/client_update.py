

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ClientUpdate:


    token: str
    pd: Decimal | None = None
    score: Decimal | None = None
    payment_capacity: Decimal | None = None
    suggested_limit: Decimal | None = None


__all__ = ["ClientUpdate"]
