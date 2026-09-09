







from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy.orm import Session, sessionmaker

try:
    from .connection import engine  # type: ignore
except Exception:
    engine = None


# If no engine is available at import time, leave SessionLocal as None so tests
# or application startup can assign it.
SessionLocal = None
if engine is not None:
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


__all__ = ["SessionLocal"]


@contextmanager
def get_db_session() -> Session:











    if SessionLocal is None:
        raise RuntimeError(
            "SessionLocal is not configured. Call build_engine()/set SessionLocal before use."
        )

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


__all__.append("get_db_session")
