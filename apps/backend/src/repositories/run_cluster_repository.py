

from __future__ import annotations

from src.schema.database.run_clusters import RunClusters
from .base_repository import BaseRepository


class RunClusterRepository(BaseRepository):


    model = RunClusters

    def get_by_run(self, run_id: int) -> list[RunClusters]:

        return self.find_by(run_id=run_id)

    def create(self, instance: RunClusters) -> RunClusters:
        """Insert a new run cluster."""
        return self._db.create(instance)

    def get_by_id(self, entity_id: int) -> RunClusters | None:

        return self._db.get_by_id(self.model, entity_id)

    def get_all(self) -> list[RunClusters]:

        return self._db.get_all(self.model)

    def find_by(self, **filters) -> list[RunClusters]:

        return self._db.find_by(self.model, **filters)


__all__ = ["RunClusterRepository"]
