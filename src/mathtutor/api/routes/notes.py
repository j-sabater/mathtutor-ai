"""Endpoint POST /api/notes/generate para generar apunte personalizado."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from mathtutor.api.schemas.v1.notes import GenerateNoteRequest, NoteResponse
from mathtutor.api.dependencies import get_db_transaction
from mathtutor.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["notes"])


@router.post(
    "/notes/generate",
    response_model=NoteResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generar apunte personalizado (async)",
)
async def generate_note(
    request: GenerateNoteRequest,
    tx = Depends(get_db_transaction),
) -> NoteResponse:
    """
    Genera un apunte PDF personalizado abordando:
    - Conceptos especificados
    - Patrones de error recurrentes
    Incluye ejemplos contrarios y práctica guiada.
    """
    logger.info("note_generation_requested", alumna_id=request.alumna_id, conceptos=request.conceptos_codigos)

    # TODO: Implementar workflow NoteGenerationWorkflow
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Endpoint no implementado aún. Requiere NoteGenerationWorkflow."
    )
