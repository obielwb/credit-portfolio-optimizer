





from __future__ import annotations

from typing import Any, Iterable, List

from sqlalchemy.orm import Session


class DBClient:






    def __init__(self, session: Session) -> None:

        self.session = session

    def create(self, instance: Any) -> Any:







        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)
        return instance

    def bulk_create(self, model: Any, rows: Iterable[dict]) -> None:






        self.session.bulk_insert_mappings(model, list(rows))
        self.session.commit()

    def get_by_id(self, model: Any, entity_id: Any) -> Any:




        return self.session.get(model, entity_id)

    def get_all(self, model: Any) -> List[Any]:

        return self.session.query(model).all()

    def find_by(self, model: Any, **filters) -> List[Any]:




        return self.session.query(model).filter_by(**filters).all()

    def exists(self, model: Any, **filters) -> bool:

        return self.session.query(model).filter_by(**filters).first() is not None

    def count(self, model: Any, **filters) -> int:

        q = self.session.query(model)
        if filters:
            q = q.filter_by(**filters)
        return q.count()

    def update(self) -> None:

        self.session.commit()

    def save(self, instance: Any) -> Any:

        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)
        return instance

    def delete(self, instance: Any) -> None:

        self.session.delete(instance)
        self.session.commit()

    def rollback(self) -> None:

        self.session.rollback()

    def close(self) -> None:

        self.session.close()

    def paginate(
        self,
        model: Any,
        page: int = 1,
        page_size: int = 100,
        filters: dict | None = None,
        order_by: Any | None = None,
    ) -> List[Any]:









        q = self.session.query(model)
        if filters:
            q = q.filter_by(**filters)
        if order_by is not None:
            q = q.order_by(order_by)
        return q.offset((page - 1) * page_size).limit(page_size).all()

    def update_by_id(self, model: Any, entity_id: Any, values: dict) -> int:
        """Perform a partial update by primary key without loading the object.

        Returns the number of rows affected.
        """
        # assume convention primary key column named 'id'
        """Partially update by primary key and return the number of affected rows."""

        pk = getattr(model, "id", None)
        if pk is None:
            raise AttributeError("Model has no attribute 'id'; cannot update by id")

        q = self.session.query(model).filter(pk == entity_id)
        rows = q.update(values, synchronize_session="fetch")
        self.session.commit()
        return rows


__all__ = ["DBClient"]
