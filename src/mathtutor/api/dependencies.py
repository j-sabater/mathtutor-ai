"""Dependencias FastAPI (DI para repositorios, LLM, OCR, etc.)."""

from __future__ import annotations

from typing import AsyncGenerator
from fastapi import Depends
from returns.result import Failure

from mathtutor.graph.session import get_neo4j_session, get_neo4j_transaction, AsyncSession, AsyncTransaction
from mathtutor.graph.repositories_impl import create_repositories, Neo4jRepositories
from mathtutor.llm.factory import LLMFactory
from mathtutor.llm.protocol import LLMProtocol
from mathtutor.ingestion.pipeline import OCRPipeline
from mathtutor.ingestion.strategies.protocol import OCRStrategy
from mathtutor.agent.tools.protocols import SymPyToolProtocol
from mathtutor.agent.tools.error_classifier import ErrorClassifierEngine
from mathtutor.core.config import settings


# ── Database Dependencies ──────────────────────────────────────────────

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency para sesión Neo4j (read)."""
    async for session in get_neo4j_session():
        yield session


async def get_db_transaction() -> AsyncGenerator[AsyncTransaction, None]:
    """Dependency para transacción Neo4j (write)."""
    async for tx in get_neo4j_transaction():
        yield tx


# ── LLM Dependencies ──────────────────────────────────────────────────

async def get_llm() -> LLMProtocol:
    """Dependency para proveedor LLM configurado."""
    result = LLMFactory.create()
    if isinstance(result, Failure):
        raise RuntimeError(f"LLM initialization failed: {result.failure()}")
    return result.unwrap()


# ── OCR Dependencies ──────────────────────────────────────────────────

async def get_ocr_pipeline() -> OCRPipeline:
    """Dependency para pipeline OCR híbrido (local + fallback)."""
    # Importar aquí para evitar dependencias circulares
    from mathtutor.ingestion.strategies.local_pix2text import Pix2TextStrategy
    from mathtutor.ingestion.strategies.api_mathpix import MathpixStrategy

    local = None
    fallback = None

    if settings.ocr_local_enabled:
        local = Pix2TextStrategy(
            model_path=settings.ocr_local_model,
            device=settings.ocr_local_device,
        )

    if settings.ocr_fallback_enabled:
        if settings.ocr_fallback_provider == "mathpix" and settings.mathpix_app_id:
            fallback = MathpixStrategy(
                app_id=settings.mathpix_app_id,
                app_key=settings.mathpix_app_key,
            )

    return OCRPipeline(
        local_strategy=local,
        fallback_strategy=fallback,
        confidence_threshold=0.7,
    )


# ── SymPy Tool Dependencies ───────────────────────────────────────────

async def get_sympy_tool() -> SymPyToolProtocol:
    """Dependency para herramienta SymPy determinista."""
    from mathtutor.agent.tools.sympy_tool import Latex2SymPyTool
    return Latex2SymPyTool(timeout_seconds=settings.sympy_timeout_seconds)


# ── Error Classifier Dependencies ─────────────────────────────────────

async def get_error_classifier() -> ErrorClassifierEngine:
    """Dependency para motor de clasificación de errores."""
    from mathtutor.agent.tools.error_classifier import create_error_classifier
    return create_error_classifier()


# ── Repository Dependencies ────────────────────────────────────────────

async def get_repositories() -> Neo4jRepositories:
    """Dependency para repositorios Neo4j con transacción."""
    from mathtutor.graph.session import get_neo4j_transaction
    async for tx in get_neo4j_transaction():
        yield await create_repositories(tx)
