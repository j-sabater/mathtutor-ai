"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mathtutor.core.config import settings
from mathtutor.core.logging import setup_logging, get_logger
from mathtutor.graph.session import init_neo4j, close_neo4j
from mathtutor.api.routes import (
    ingest_router,
    review_router,
    correction_router,
    progress_router,
    notes_router,
    agent_router,
    websocket_router,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión de ciclo de vida: startup/shutdown."""
    # Startup
    setup_logging()
    logger.info("app_starting", env=settings.app_env)
    await init_neo4j()
    logger.info("app_started")

    yield

    # Shutdown
    logger.info("app_shutting_down")
    await close_neo4j()
    logger.info("app_shutdown_complete")


def create_app() -> FastAPI:
    """Factory para crear la aplicación FastAPI."""
    app = FastAPI(
        title="MathTutor-AI API",
        description="API REST para sistema agéntico de tutoría matemática (Matemáticas II: Cálculo)",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app_env == "development" else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(ingest_router)
    app.include_router(review_router)
    app.include_router(correction_router)
    app.include_router(progress_router)
    app.include_router(notes_router)
    app.include_router(agent_router)
    app.include_router(websocket_router)

    # Health check
    @app.get("/health", tags=["health"])
    async def health_check():
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()


def run():
    """Entry point para uvicorn."""
    import uvicorn
    uvicorn.run(
        "mathtutor.api.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run()
