"""Repository for the PortfolioResults entity."""

from __future__ import annotations

from decimal import Decimal

from src.schema.database.portfolio_results import PortfolioResults
from src.models.result import PortfolioResult
from .base_repository import BaseRepository


class ResultRepository(BaseRepository):


    model = PortfolioResults

    def get_by_run_id(self, run_id: int) -> PortfolioResults | None:

        return self.find_one_by(run_id=run_id)

    def create_from_result_portfolio(
        self, result: PortfolioResult, run_id: int
    ) -> PortfolioResults:

        orm = PortfolioResults(
            run_id=run_id,
            total_clients=result.total_clients,
            total_limit=result.total_limit,
            total_income=result.total_income,
            total_loss=result.total_loss,
            total_return=result.total_return,
            financial_default_rate=result.financial_default_rate,
            baseline_default_rate=result.baseline_default_rate,
        )
        return self.create(orm)

    def get_latest(self) -> PortfolioResults | None:

        all_res = self.get_all()
        return max(all_res, key=lambda r: r.id) if all_res else None

    # CRUD helpers
    def create(self, instance: PortfolioResults) -> PortfolioResults:
        """Insert a new portfolio result."""
        return self._db.create(instance)

    def get_by_id(self, entity_id: int) -> PortfolioResults | None:

        return self._db.get_by_id(self.model, entity_id)

    def get_all(self) -> list[PortfolioResults]:

        return self._db.get_all(self.model)

    def find_by(self, **filters) -> list[PortfolioResults]:

        return self._db.find_by(self.model, **filters)

    def find_one_by(self, **filters) -> PortfolioResults | None:

        results = self.find_by(**filters)
        return results[0] if results else None

    def update_by_id(self, entity_id: int, values: dict) -> int:

        return self._db.update_by_id(self.model, entity_id, values)


__all__ = ["ResultRepository"]
