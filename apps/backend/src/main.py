"""FastAPI backend application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import contextlib

from src.controllers.comparison_controller import router as comparison_router
from src.controllers.health_controller import router as health_router
from src.controllers.ingestion_controller import router as ingestion_router
from src.controllers.optimization_controller import router as optimization_router
from src.controllers.parameters_controller import router as parameters_router
from src.controllers.statistics_controller import router as statistics_router
from src.utils.cors import get_cors_allow_credentials, get_cors_allowed_origins
from src.utils.db.bootstrap import bootstrap_database

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa recursos no startup da aplicacao."""
    bootstrap_database()
    yield

def create_app() -> FastAPI:

    app = FastAPI(title="Optimizer Backend", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_allowed_origins(),
        allow_credentials=get_cors_allow_credentials(),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(comparison_router)
    app.include_router(ingestion_router)
    app.include_router(optimization_router)
    app.include_router(parameters_router)
    app.include_router(statistics_router)

    @app.get("/", tags=["health"])
    def root() -> dict[str, str]:
        """GET / — health check basico do servico."""
        return {"status": "ok", "service": "optimizer-backend"}

    return app


app = create_app()
