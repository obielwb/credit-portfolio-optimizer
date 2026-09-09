"""Repository for the CsvFile entity."""

from __future__ import annotations

from src.schema.database.csv_file import CsvFile
from .base_repository import BaseRepository


class CsvFileRepository(BaseRepository):


    model = CsvFile

    def get_by_name(self, name: str) -> CsvFile | None:

        return self.find_one_by(name=name)

    def get_latest(self) -> CsvFile | None:

        all_csvs = self.get_all()
        return max(all_csvs, key=lambda a: a.id) if all_csvs else None



    def create(self, instance: CsvFile) -> CsvFile:
        """Insert a new CSV file record."""
        return self._db.create(instance)

    def get_by_id(self, entity_id: int) -> CsvFile | None:

        return self._db.get_by_id(self.model, entity_id)

    def get_all(self) -> list[CsvFile]:

        return self._db.get_all(self.model)

    def find_by(self, **filters) -> list[CsvFile]:

        return self._db.find_by(self.model, **filters)

    def find_one_by(self, **filters) -> CsvFile | None:

        results = self.find_by(**filters)
        return results[0] if results else None

    def update_by_id(self, entity_id: int, values: dict) -> int:

        return self._db.update_by_id(self.model, entity_id, values)

    def bulk_create(self, rows: list[dict]) -> None:
        """Insere multiplos files CSV em lote."""
        return self._db.bulk_create(self.model, rows)


__all__ = ["CsvFileRepository"]
