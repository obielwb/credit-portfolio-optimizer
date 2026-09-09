

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TypeAlias


@dataclass(frozen=True, slots=True)
class MultiplierPD:


    min_pd: Decimal
    max_pd: Decimal
    multiplier: Decimal


TabelaMultipliers: TypeAlias = list[MultiplierPD]


__all__ = ["MultiplierPD", "TabelaMultipliers"]
