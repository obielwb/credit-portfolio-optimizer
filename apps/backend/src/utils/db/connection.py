






from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def build_database_url() -> str:












    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    connection_params = {
        "POSTGRES_HOST": os.getenv("POSTGRES_HOST"),
        "POSTGRES_PORT": os.getenv("POSTGRES_PORT"),
        "POSTGRES_DB": os.getenv("POSTGRES_DB"),
        "POSTGRES_USER": os.getenv("POSTGRES_USER"),
        "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD"),
    }

    missing_variables = [name for name, value in connection_params.items() if not value]

    if missing_variables:
        missing_list = ", ".join(missing_variables)
        raise RuntimeError(
            f"Missing database configuration. Set DATABASE_URL or strictly define: {missing_list}."
        )

    postgres_host = connection_params["POSTGRES_HOST"]
    postgres_port = connection_params["POSTGRES_PORT"]
    postgres_db = connection_params["POSTGRES_DB"]
    postgres_user = connection_params["POSTGRES_USER"]
    postgres_password = connection_params["POSTGRES_PASSWORD"]

    return (
        "postgresql+psycopg2://"
        f"{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
    )


def build_engine(database_url: str | None = None) -> Engine:







    resolved_url = database_url or build_database_url()
    return create_engine(resolved_url, pool_pre_ping=True)
