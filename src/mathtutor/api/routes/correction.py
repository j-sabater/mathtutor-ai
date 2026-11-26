"""Endpoint GET /api/intentos/{intento_id}/correction para obtener resultado."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from mathtutor.api.schemas.v1.correction import CorrectionResult
from mathtutor.api.dependencies import get_db_session
from mathtutor.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["correction"])


@router.get(
    "/intentos/{intento_id}/correction",
    response_model=CorrectionResult,
    summary="Obtener resultado de corrección de un intento",
)
async def get_correction(
    intento_id: str,
    session = Depends(get_db_session),
) -> CorrectionResult:
    """
    Retorna el resultado completo de la corrección:
    - Puntuación global
    - Feedback por paso
    - Errores detectados
    - Mastery actualizado
    - Ejercicio recomendado
    """
    logger.info("correction_requested", intento_id=intento_id)

    # TODO: Implementar consulta real a BD
    # Por ahora retorna mock para testing
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Endpoint no implementado aún. Requiere workflow completo."
    )
