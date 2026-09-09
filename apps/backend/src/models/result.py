

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.models.client import OptimizationClient


@dataclass(frozen=True, slots=True)
class ClientEvaluation:


    client: OptimizationClient
    limit_candidate: Decimal
    expected_income: Decimal
    expected_loss: Decimal
    expected_return: Decimal


@dataclass(frozen=True, slots=True)
class ClientResult:


    client: OptimizationClient
    suggested_limit: Decimal
    expected_income: Decimal
    expected_loss: Decimal
    expected_return: Decimal


@dataclass(frozen=True, slots=True)
class PortfolioResult:
    """Aggregate portfolio summary after optimization."""

    clients: list[ClientResult]
    total_limit: Decimal
    total_income: Decimal
    total_loss: Decimal
    total_return: Decimal
    financial_default_rate: Decimal
    baseline_default_rate: Decimal
    algorithm: str = "not_provided"

    @property
    def total_clients(self) -> int:
        """Number of clients included in the result."""

        return len(self.clients)

    @property
    def approval_rate(self) -> Decimal:


        if not self.clients:
            return Decimal("0")

        approved = sum(
            1 for result in self.clients if result.suggested_limit > Decimal("0")
        )
        return Decimal(approved) / Decimal(len(self.clients))

    @property
    def total_clients_por_range_limit(self) -> dict[str, int]:


        ranges = {
            "0-1k": (Decimal("0"), Decimal("1000")),
            "1k-5k": (Decimal("1000"), Decimal("5000")),
            "5k-10k": (Decimal("5000"), Decimal("10000")),
            "10k-15k": (Decimal("10000"), Decimal("15000")),
            "15k-20k": (Decimal("15000"), Decimal("20000")),
            "20k-25k": (Decimal("20000"), Decimal("25000")),
        }
        totais = dict.fromkeys(ranges, 0)

        for result in self.clients:
            for name, (limit_inferior, limit_superior) in ranges.items():
                dentro_da_range = (
                    limit_inferior
                    <= result.suggested_limit
                    < limit_superior
                )
                dentro_da_ultima_range = (
                    name == "20k-25k"
                    and result.suggested_limit == limit_superior
                )
                if dentro_da_range or dentro_da_ultima_range:
                    totais[name] += 1
                    break

        return totais


__all__ = ["ClientEvaluation", "PortfolioResult", "ClientResult"]
