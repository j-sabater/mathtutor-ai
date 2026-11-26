"""Endpoint POST /api/ingest para ingesta de intentos."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import HttpUrl

from mathtutor.api.schemas.v1.ingest import IngestRequest, IngestResponse
from mathtutor.api.dependencies import get_ocr_pipeline
from mathtutor.ingestion.pipeline import OCRPipeline
from mathtutor.graph.session import get_db_transaction
from mathtutor.graph.repositories import IntentoRepository
from mathtutor.domain.entities import EstadoIntento
from mathtutor.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["ingest"])


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingesta de intento (OCR + persistencia)",
)
async def ingest_intento(
    request: IngestRequest,
    ocr_pipeline: OCRPipeline = Depends(get_ocr_pipeline),
    tx = Depends(get_db_transaction),
) -> IngestResponse:
    """
    Procesa imágenes/PDF subidas por la alumna:
    1. Descarga imágenes desde URLs
    2. Ejecuta pipeline OCR híbrido (local → fallback)
    3. Estructura LaTeX en pasos
    4. Persiste Intento en estado 'pendiente'
    5. Retorna LaTeX extraído para revisión humana
    """
    trace_id = "trace-" + str(hash(str(request.imagenes)))[:8]
    logger.info("ingest_start", trace_id=trace_id, ejercicio_id=request.ejercicio_id, num_images=len(request.imagenes))

    try:
        # 1. Descargar imágenes
        imagenes_bytes = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for url in request.imagenes:
                resp = await client.get(str(url))
                resp.raise_for_status()
                imagenes_bytes.append(resp.content)

        # 2. Ejecutar OCR
        ocr_result = await ocr_pipeline.process(
            images=imagenes_bytes,
            context={"ejercicio_id": request.ejercicio_id}
        )

        # 3. Determinar si requiere revisión
        requiere_revision = ocr_result.confidence < 0.7
        estado = EstadoIntento.ERROR_OCR if requiere_revision else EstadoIntento.PENDIENTE

        # 4. Persistir Intento
        # TODO: Usar IntentoRepository real cuando esté implementado
        # Por ahora retornamos respuesta mock
        intento_id = "intento-" + trace_id

        logger.info("ingest_complete", trace_id=trace_id, intento_id=intento_id, estado=estado.value)

        return IngestResponse(
            trace_id=trace_id,
            intento_id=intento_id,
            estado=estado,
            latex_extraido=ocr_result.latex_raw,
            pasos_detectados=len(ocr_result.pasos_structurados),
            confidence=ocr_result.confidence,
            strategy_used=ocr_result.strategy_used,
            fallback_used=ocr_result.fallback_used,
            requiere_revision=requiere_revision,
        )

    except httpx.HTTPError as e:
        logger.error("ingest_download_failed", trace_id=trace_id, error=str(e))
        raise HTTPException(status_code=400, detail=f"Error descargando imágenes: {e}")
    except Exception as e:
        logger.error("ingest_failed", trace_id=trace_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Error en ingesta: {e}")
