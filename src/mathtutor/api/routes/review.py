"""Endpoint POST /api/intentos/{trace_id}/review para revisión OCR."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from mathtutor.api.schemas.v1.review import OCRReviewRequest, OCRReviewResponse
from mathtutor.api.dependencies import get_db_transaction
from mathtutor.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["review"])


@router.post(
    "/intentos/{trace_id}/review",
    response_model=OCRReviewResponse,
    summary="Revisión humana de LaTeX extraído (Human-in-the-loop)",
)
async def review_ocr(
    trace_id: str,
    request: OCRReviewRequest,
    tx = Depends(get_db_transaction),
) -> OCRReviewResponse:
    """
    Endpoint para que el profesor apruebe o corrija el LaTeX extraído por OCR.
    - action="approve": Continúa con corrección automática
    - action="correct": Valida LaTeX corregido y continúa
    """
    logger.info("review_received", trace_id=trace_id, action=request.action)

    if request.action == "approve":
        # TODO: Actualizar estado en BD y disparar workflow de corrección
        return OCRReviewResponse(
            status="accepted",
            trace_id=trace_id,
            mensaje="LaTeX aprobado. Iniciando corrección automática...",
        )

    elif request.action == "correct":
        if not request.corrected_latex:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="corrected_latex es requerido cuando action='correct'"
            )

        # TODO: Validar LaTeX corregido con SymPy
        # TODO: Re-estructurar pasos y actualizar Intento

        return OCRReviewResponse(
            status="accepted",
            trace_id=trace_id,
            mensaje="LaTeX corregido aceptado. Iniciando corrección...",
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Acción inválida: {request.action}"
        )
