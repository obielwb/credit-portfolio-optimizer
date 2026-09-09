

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from src.models.parameters import DEFAULT_MULTIPLIERS, OptimizationParameters
from src.repositories import ParametersRepository
from src.schema.database.parameters import Parameters
from src.utils.db.connection import build_engine


def import_all_models() -> None:


    from src.schema.database import (  # noqa: F401
        CsvFile,
        Base,
        Client,
        ClientHistory,
        Parameters,
        PortfolioResults,
        Run,
    )
    from src.schema.database.run_clusters import RunClusters  # noqa: F401


def _ensure_postgresql_enum_types(engine: Engine) -> None:


    if engine.dialect.name != "postgresql":
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                DO $enum$
                BEGIN
                    CREATE TYPE change_type_enum AS ENUM (
                        'new_client', 'updated_limit'
                    );
                EXCEPTION
                    WHEN duplicate_object THEN NULL;
                END
                $enum$;
                """
            )
        )


def _migrate_parameters_columns(engine: Engine) -> None:
    """Add missing table columns idempotently."""

    if engine.dialect.name != "postgresql":
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                ALTER TABLE parameters
                    ADD COLUMN IF NOT EXISTS filter BOOLEAN NOT NULL DEFAULT TRUE;
                DO $migrate$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'parameters'
                          AND column_name = 'constraint_flag_1'
                    ) THEN
                        UPDATE parameters
                            SET filter = constraint_flag_1
                            WHERE filter IS DISTINCT FROM constraint_flag_1;
                        ALTER TABLE parameters DROP COLUMN constraint_flag_1;
                    END IF;
                END
                $migrate$;
                ALTER TABLE clients
                    ADD COLUMN IF NOT EXISTS filter_flag BOOLEAN NOT NULL DEFAULT FALSE;
                ALTER TABLE results
                    ADD COLUMN IF NOT EXISTS approved INTEGER;
                ALTER TABLE results
                    ADD COLUMN IF NOT EXISTS approval_rate NUMERIC(8, 6);
                """
            )
        )


def create_schema(engine: Engine | None = None) -> Engine:


    import_all_models()
    from src.schema.database.base import Base

    resolved_engine = engine or build_engine()
    _ensure_postgresql_enum_types(resolved_engine)
    try:
        Base.metadata.create_all(resolved_engine, checkfirst=True)
    except IntegrityError:
        # Corrida ao criar tipos ENUM entre processos concorrentes.
        Base.metadata.create_all(resolved_engine, checkfirst=True)
    _migrate_parameters_columns(resolved_engine)
    return resolved_engine


def configure_session_local(engine: Engine) -> sessionmaker[Session]:


    import src.utils.db.session as db_session_module

    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    db_session_module.SessionLocal = SessionLocal
    return SessionLocal


def default_parameters_values() -> dict[str, Any]:
    """Default values aligned with the domain (`OptimizationParameters`)."""

    defaults = OptimizationParameters(
        min_limit=Decimal("200.00"),
        max_rejected_limit=Decimal("25000.00"),
        multipliers=list(DEFAULT_MULTIPLIERS),
    )
    return {
        "utilization_rate": defaults.utilization_rate,
        "lgd": defaults.lgd,
        "min_pd": defaults.min_pd,
        "max_pd": defaults.max_pd,
        "filter": defaults.filter,
        "max_limit": defaults.max_limit,
        "baseline_default_rate": defaults.baseline_default_rate,
        "min_limit": defaults.min_limit,
        "discretize": defaults.discretize,
        "interchange": defaults.interchange,
        "max_rejected_limit": defaults.max_rejected_limit,
        "enabled": defaults.enabled,
        "n_clusters": defaults.n_clusters,
        "max_clients_per_cluster": defaults.max_clients_per_cluster,
        "min_clusters": defaults.min_clusters,
        "multipliers": serialize_multipliers(defaults.multipliers),
    }


def serialize_multipliers(
    multipliers: list[Any],
) -> list[dict[str, str]]:


    return [
        {
            "min_pd": str(item.min_pd),
            "max_pd": str(item.max_pd),
            "multiplier": str(item.multiplier),
        }
        for item in multipliers
    ]


def seed_default_parameters(session: Session) -> int | None:
    """Insert default parameters when the table is empty."""

    params_repo = ParametersRepository(session)
    if params_repo.get_latest() is not None:
        return None

    values = default_parameters_values()
    created = params_repo.create(
        Parameters(
            utilization_rate=values["utilization_rate"],
            lgd=values["lgd"],
            min_pd=values["min_pd"],
            max_pd=values["max_pd"],
            filter=values["filter"],
            max_limit=values["max_limit"],
            baseline_default_rate=values["baseline_default_rate"],
            min_limit=values["min_limit"],
            discretize=values["discretize"],
            interchange=values["interchange"],
            max_rejected_limit=values["max_rejected_limit"],
            enabled=values["enabled"],
            n_clusters=values["n_clusters"],
            max_clients_per_cluster=values["max_clients_per_cluster"],
            min_clusters=values["min_clusters"],
            multipliers=values["multipliers"],
        )
    )
    return created.id


def bootstrap_database(
    engine: Engine | None = None,
    *,
    seed: bool = True,
    configure_session: bool = True,
    ensure_schema: bool = True,
) -> tuple[Engine, int | None]:
    """Create the ORM schema and idempotently seed parameters."""

    resolved_engine = engine or build_engine()
    if ensure_schema:
        resolved_engine = create_schema(resolved_engine)

    if configure_session:
        configure_session_local(resolved_engine)

    seeded_id: int | None = None
    if seed:
        SessionLocal = sessionmaker(
            bind=resolved_engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
        with SessionLocal() as session:
            seeded_id = seed_default_parameters(session)
            session.commit()

    return resolved_engine, seeded_id


__all__ = [
    "bootstrap_database",
    "configure_session_local",
    "create_schema",
    "default_parameters_values",
    "import_all_models",
    "seed_default_parameters",
    "serialize_multipliers",
    "_migrate_parameters_columns",
]
