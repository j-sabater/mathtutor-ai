"""Endpoints para gestión de workflows del agente (LangGraph)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from mathtutor.api.dependencies import get_db_transaction
from mathtutor.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["agent"])


class WorkflowStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    trace_id: str
    current_node: str
    status: str  # "running", "interrupted", "completed", "failed"
    error: str | None = None


@router.get(
    "/workflows/{trace_id}/status",
    response_model=WorkflowStatusResponse,
    summary="Obtener estado de workflow",
)
async def get_workflow_status(
    trace_id: str,
    tx = Depends(get_db_transaction),
) -> WorkflowStatusResponse:
    """Consulta el estado actual de un workflow en ejecución."""
    logger.info("workflow_status_requested", trace_id=trace_id)

    # TODO: Implementar consulta a checkpointer (SqliteSaver)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Requiere integración con LangGraph checkpointer."
    )


@router.post(
    "/workflows/{trace_id}/resume",
    response_model=WorkflowStatusResponse,
    summary="Reanudar workflow interrumpido",
)
async def resume_workflow(
    trace_id: str,
    payload: dict,  # OCRReviewRequest u otro según nodo interrumpido
    tx = Depends(get_db_transaction),
) -> WorkflowStatusResponse:
    """Reanuda un workflow pausado en interrupt point (ej. review_ocr)."""
    logger.info("workflow_resume_requested", trace_id=trace_id)

    # TODO: Implementar graph.ainvoke(Command(resume=payload), config)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Requiere integración con LangGraph checkpointer."
    )
