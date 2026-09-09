"""Repository for the ClientHistory audit entity."""

from __future__ import annotations

from typing import Any

from src.schema.database.client_history import ClientHistory
from src.custom_types import ClientChangeType
from .base_repository import BaseRepository


class ClientHistoryRepository(BaseRepository):


    model = ClientHistory

    def get_by_token(self, token: str) -> list[ClientHistory]:

        return self.find_by(token=token)

    def register_change(
        self,
        token: str,
        tipo: ClientChangeType,
        current_state: dict[str, Any],
        previous_state: dict[str, Any] | None = None,
        *,
        run_id: int | None = None,
    ) -> ClientHistory:

        entry = ClientHistory(
            token=token,
            change_type=tipo,
            previous_state=previous_state,
            current_state=current_state,
            run_id=run_id,
        )
        return self.create(entry)

    def bulk_register_changes(self, rows: list[dict[str, Any]]) -> None:








        if not rows:
            return
        self.session.bulk_insert_mappings(self.model, rows)

    # CRUD helpers
    def create(self, instance: ClientHistory) -> ClientHistory:

        return self._db.create(instance)

    def get_by_id(self, entity_id: int) -> ClientHistory | None:

        return self._db.get_by_id(self.model, entity_id)

    def get_all(self) -> list[ClientHistory]:

        return self._db.get_all(self.model)

    def find_by(self, **filters) -> list[ClientHistory]:

        return self._db.find_by(self.model, **filters)

    def find_one_by(self, **filters) -> ClientHistory | None:

        results = self.find_by(**filters)
        return results[0] if results else None


__all__ = ["ClientHistoryRepository"]
