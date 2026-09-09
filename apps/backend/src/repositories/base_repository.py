








from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy.orm import Session

from src.utils.db import DBClient


ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):













    model: Any = None

    def __init__(self, session: Session) -> None:

        if self.__class__.model is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define the 'model' class attribute."
            )
        self.session = session
        self._db = DBClient(session)


__all__ = ["BaseRepository"]
