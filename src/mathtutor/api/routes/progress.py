"""Endpoint GET /api/progress/{alumna_id} para dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from mathtutor.api.schemas.v1.progress import ProgressResponse
from mathtutor.api.dependencies import get_db_session
from mathtutor.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["progress"])


@router.get(
    "/progress/{alumna_id}",
    response_model=ProgressResponse,
    summary="Obtener progreso de alumna (Dashboard)",
)
async def get_progress(
    alumna_id: str,
    session = Depends(get_db_session),
) -> ProgressResponse:
    """
    Retorna dashboard completo:
    - Mastery por concepto
    - Top patrones de error (30 días)
    - Racha actual
    - Próxima recomendación
    """
    logger.info("progress_requested", alumna_id=alumna_id)

    # TODO: Implementar consulta real a BD
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Endpoint no implementado aún. Requiere GraphRepository.get_student_profile."
    )
