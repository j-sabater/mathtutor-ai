"""Routers FastAPI."""

from mathtutor.api.routes.ingest import router as ingest_router
from mathtutor.api.routes.review import router as review_router
from mathtutor.api.routes.correction import router as correction_router
from mathtutor.api.routes.progress import router as progress_router
from mathtutor.api.routes.notes import router as notes_router
from mathtutor.api.routes.agent import router as agent_router
from mathtutor.api.routes.websocket import router as websocket_router

__all__ = [
    "ingest_router",
    "review_router",
    "correction_router",
    "progress_router",
    "notes_router",
    "agent_router",
    "websocket_router",
]
