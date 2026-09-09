

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session, selectinload

from src.repositories.client_repository import ClientRepository
from src.schema.database.client import Client
from src.schema.database.client_history import ClientHistory
from src.schema.database.run import Run


@dataclass(frozen=True, slots=True)
class ClientRunSnapshot:


    token: str
    last_run_id: int
    last_suggested_limit: Decimal
    payment_capacity: Decimal
    score: Decimal
    pd: Decimal
    cohort_reference: str | None = None
    filter_flag: bool = False


class ComparisonRepository:


    def __init__(self, session: Session) -> None:

        self.session = session
        self._client_repo = ClientRepository(session)

    def get_run_with_context(self, run_id: int) -> Run | None:


        return (
            self.session.query(Run)
            .options(
                selectinload(Run.result),
                selectinload(Run.file_csv),
                selectinload(Run.parameters),
                selectinload(Run.clusters),
            )
            .filter(Run.id == run_id)
            .one_or_none()
        )

    def get_clients_by_run(self, run_id: int) -> list[ClientRunSnapshot | Client]:






        audit_rows = (
            self.session.query(ClientHistory)
            .filter(ClientHistory.run_id == run_id)
            .order_by(ClientHistory.id)
            .all()
        )
        if not audit_rows:
            return self._client_repo.get_by_run(run_id)

        tokens = [row.token for row in audit_rows]
        clients_by_token = {
            client.token: client
            for client in self.session.query(Client)
            .filter(Client.token.in_(tokens))
            .all()
        }

        snapshots: list[ClientRunSnapshot] = []
        seen_tokens: set[str] = set()
        for row in audit_rows:
            if row.token in seen_tokens:
                continue
            seen_tokens.add(row.token)
            snapshots.append(
                self._snapshot_from_audit_row(row, clients_by_token.get(row.token), run_id)
            )
        return snapshots

    @staticmethod
    def _snapshot_from_audit_row(
        row: ClientHistory,
        client: Client | None,
        run_id: int,
    ) -> ClientRunSnapshot:


        state: dict[str, Any] = row.current_state or {}
        limit = Decimal(str(state.get("suggested_limit", 0)))

        def _decimal_field(key: str, fallback: Decimal | None) -> Decimal:


            if key in state and state[key] is not None:
                return Decimal(str(state[key]))
            if fallback is not None:
                return fallback
            return Decimal("0")

        return ClientRunSnapshot(
            token=row.token,
            last_run_id=run_id,
            last_suggested_limit=limit,
            payment_capacity=_decimal_field(
                "payment_capacity",
                client.payment_capacity if client else None,
            ),
            score=_decimal_field("score", client.score if client else None),
            pd=_decimal_field("pd", client.pd if client else None),
            cohort_reference=state.get("cohort_reference")
            if state.get("cohort_reference") is not None
            else (client.cohort_reference if client else None),
            filter_flag=bool(state.get("filter_flag", False)),
        )


__all__ = ["ClientRunSnapshot", "ComparisonRepository"]
