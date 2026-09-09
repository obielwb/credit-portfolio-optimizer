"""Client domain models."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class OptimizationClient:


    token: str
    pd: Decimal
    payment_capacity: Decimal
    propensity_score: Decimal
    filter_flag: bool = False
    cohort_reference: str | None = None


__all__ = ["OptimizationClient"]
