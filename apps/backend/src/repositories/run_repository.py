"""Repository for the Run entity."""

from __future__ import annotations

from datetime import datetime

from src.schema.database.run import Run
from .base_repository import BaseRepository


class RunRepository(BaseRepository):


    model = Run

    def get_by_file_csv(self, csv_file_id: int) -> list[Run]:

        return self.find_by(csv_file_id=csv_file_id)

    def get_latest_by_file(self, csv_file_id: int) -> Run | None:

        runs = self.get_by_file_csv(csv_file_id)
        return max(runs, key=lambda r: r.id) if runs else None

    def get_completed(self) -> list[Run]:

        return self.find_by(status="success")

    def mark_success(self, run_id: int, time_ms: int) -> None:

        self.update_by_id(
            run_id,
            {"status": "success", "execution_time_ms": time_ms, "error_reason": None},
        )

    def mark_error(
        self,
        run_id: int,
        time_ms: int = 0,
        *,
        error_reason: str | None = None,
    ) -> None:
        """Mark the run as failed and record the reason."""
        values: dict[str, object] = {
            "status": "error",
            "execution_time_ms": time_ms,
        }
        if error_reason is not None:
            values["error_reason"] = error_reason
        self.update_by_id(run_id, values)

    def update_progress(
        self,
        run_id: int,
        *,
        state_operacional: str,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> None:
        """Update the run's operational state and timestamps."""
        values: dict[str, object] = {
            "state_operacional": state_operacional,
        }
        if started_at is not None:
            values["started_at"] = started_at
        if finished_at is not None:
            values["finished_at"] = finished_at
        self.update_by_id(run_id, values)

    # CRUD helpers
    def create(self, instance: Run) -> Run:

        return self._db.create(instance)

    def get_by_id(self, entity_id: int) -> Run | None:

        return self._db.get_by_id(self.model, entity_id)

    def get_all(self) -> list[Run]:

        return self._db.get_all(self.model)

    def find_by(self, **filters) -> list[Run]:

        return self._db.find_by(self.model, **filters)

    def find_one_by(self, **filters) -> Run | None:

        results = self.find_by(**filters)
        return results[0] if results else None

    def update_by_id(self, entity_id: int, values: dict) -> int:

        return self._db.update_by_id(self.model, entity_id, values)


__all__ = ["RunRepository"]
