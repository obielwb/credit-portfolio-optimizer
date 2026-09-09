"""Repository for the Parameters entity."""

from __future__ import annotations

from src.schema.database.parameters import Parameters
from .base_repository import BaseRepository


class ParametersRepository(BaseRepository):


    model = Parameters

    def get_latest(self) -> Parameters | None:

        all_params = self.get_all()
        return max(all_params, key=lambda p: p.id) if all_params else None

    def get_latest_or_raise(self) -> Parameters:

        params = self.get_latest()
        if not params:
            raise ValueError(
                "No parameter set was found. "
                "Configure the parameters before starting a run."
            )
        return params

    # CRUD helpers
    def create(self, instance: Parameters) -> Parameters:
        """Insert a new parameter set."""
        return self._db.create(instance)

    def get_by_id(self, entity_id: int) -> Parameters | None:

        return self._db.get_by_id(self.model, entity_id)

    def get_all(self) -> list[Parameters]:

        return self._db.get_all(self.model)

    def find_by(self, **filters) -> list[Parameters]:

        return self._db.find_by(self.model, **filters)

    def find_one_by(self, **filters) -> Parameters | None:

        results = self.find_by(**filters)
        return results[0] if results else None

    def update_by_id(self, entity_id: int, values: dict) -> int:

        return self._db.update_by_id(self.model, entity_id, values)


__all__ = ["ParametersRepository"]
