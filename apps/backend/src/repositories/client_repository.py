"""Repository for the Client entity."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from src.models.client import OptimizationClient
from src.schema.database.client import Client
from .base_repository import BaseRepository

LIMIT_PENDING = Decimal("0")


@dataclass(frozen=True, slots=True)
class ClientState:


    id: int
    last_run_id: int
    last_suggested_limit: Decimal


class ClientRepository(BaseRepository):


    model = Client

    def get_by_token(self, token: str) -> Client | None:

        return self.find_one_by(token=token)

    def get_by_run(self, run_id: int) -> list[Client]:

        return self.find_by(last_run_id=run_id)

    def upsert_client(
        self,
        token: str,
        run_id: int,
        suggested_limit: Decimal,
        payment_capacity: Decimal,
        score: Decimal,
        pd: Decimal,
        cohort_reference: str | None = None,
        filter_flag: bool = False,
    ) -> Client:

        existing = self.get_by_token(token)
        values = {
            "last_run_id": run_id,
            "last_suggested_limit": suggested_limit,
            "payment_capacity": payment_capacity,
            "score": score,
            "pd": pd,
            "filter_flag": filter_flag,
        }
        if cohort_reference is not None:
            values["cohort_reference"] = cohort_reference

        if existing:
            self.update_by_id(existing.id, values)
            return self.get_by_id(existing.id)

        new = Client(
            token=token,
            last_run_id=run_id,
            last_suggested_limit=suggested_limit,
            payment_capacity=payment_capacity,
            score=score,
            pd=pd,
            filter_flag=filter_flag,
            cohort_reference=cohort_reference,
        )
        return self.create(new)



    _BULK_QUERY_CHUNK = 10_000

    def fetch_states_by_tokens(
        self, tokens: list[str]
    ) -> dict[str, "ClientState"]:






        states: dict[str, ClientState] = {}
        for start in range(0, len(tokens), self._BULK_QUERY_CHUNK):
            chunk = tokens[start : start + self._BULK_QUERY_CHUNK]
            rows = (
                self.session.query(
                    Client.id,
                    Client.token,
                    Client.last_run_id,
                    Client.last_suggested_limit,
                )
                .filter(Client.token.in_(chunk))
                .all()
            )
            for cid, token, last_run_id, last_limit in rows:
                states[token] = ClientState(
                    id=cid,
                    last_run_id=last_run_id,
                    last_suggested_limit=last_limit,
                )
        return states

    def bulk_write(
        self,
        *,
        inserts: list[dict[str, Any]],
        updates: list[dict[str, Any]],
    ) -> None:





        if inserts:
            self.session.bulk_insert_mappings(Client, inserts)
        if updates:
            self.session.bulk_update_mappings(Client, updates)

    def bulk_upsert_from_ingestion(
        self, clients: list[OptimizationClient], run_id: int
    ) -> None:






        if not clients:
            return


        por_token: dict[str, OptimizationClient] = {c.token: c for c in clients}
        states = self.fetch_states_by_tokens(list(por_token.keys()))

        inserts: list[dict[str, Any]] = []
        updates: list[dict[str, Any]] = []
        for token, client in por_token.items():
            values = {
                "last_run_id": run_id,
                "last_suggested_limit": LIMIT_PENDING,
                "payment_capacity": client.payment_capacity,
                "score": client.propensity_score,
                "pd": client.pd,
                "filter_flag": client.filter_flag,
                "cohort_reference": client.cohort_reference,
            }
            existing = states.get(token)
            if existing is None:
                inserts.append({"token": token, **values})
            else:
                updates.append({"id": existing.id, **values})

        self.bulk_write(inserts=inserts, updates=updates)
        self.session.commit()


    def create(self, instance: Client) -> Client:
        """Insert a new client into the database."""
        return self._db.create(instance)

    def get_by_id(self, entity_id: int) -> Client | None:

        return self._db.get_by_id(self.model, entity_id)

    def get_all(self) -> list[Client]:

        return self._db.get_all(self.model)

    def find_by(self, **filters) -> list[Client]:

        return self._db.find_by(self.model, **filters)

    def find_one_by(self, **filters) -> Client | None:

        results = self.find_by(**filters)
        return results[0] if results else None

    def update_by_id(self, entity_id: int, values: dict) -> int:

        return self._db.update_by_id(self.model, entity_id, values)

    def bulk_create(self, rows: list[dict]) -> None:
        """Insere multiplos clients em lote."""
        return self._db.bulk_create(self.model, rows)


__all__ = ["ClientRepository"]
