"""Orquestador híbrido OCR (Local → Fallback API)."""

from __future__ import annotations

import structlog
from typing import Optional
from dataclasses import dataclass

from mathtutor.ingestion.strategies.protocol import OCRStrategy, OCRRequest, OCRResponse
from mathtutor.domain.value_objects import OCRResult, PasoMatematico

logger = structlog.get_logger(__name__)


class OCRPipelineError(Exception):
    """Error cuando todas las estrategias OCR fallan."""
    pass


@dataclass
class OCRPipeline:
    """Pipeline híbrido: intenta local primero, luego fallback API."""

    local_strategy: Optional[OCRStrategy] = None
    fallback_strategy: Optional[OCRStrategy] = None
    confidence_threshold: float = 0.7

    async def process(self, images: list[bytes], context: dict) -> OCRResult:
        request = OCRRequest(images=images, context=context)

        # 1. Intentar estrategia local si disponible
        if self.local_strategy:
            result = await self.local_strategy.process(request)
            if result.is_success():
                resp: OCRResponse = result.unwrap()
                if resp.confidence >= self.confidence_threshold:
                    return OCRResult(
                        latex_raw=resp.latex_raw,
                        pasos_structurados=await self._structure_steps(resp.latex_raw),
                        strategy=resp.strategy_name,
                        confidence=resp.confidence,
                        fallback_used=False,
                        imagenes_paths=[]
                    )
                # Confianza baja → log y continuar a fallback
                logger.warning("low_confidence_local_ocr",
                              strategy=resp.strategy_name,
                              confidence=resp.confidence,
                              threshold=self.confidence_threshold)

        # 2. Fallback API
        if self.fallback_strategy:
            result = await self.fallback_strategy.process(request)
            if result.is_success():
                resp: OCRResponse = result.unwrap()
                return OCRResult(
                    latex_raw=resp.latex_raw,
                    pasos_structurados=await self._structure_steps(resp.latex_raw),
                    strategy=resp.strategy_name,
                    confidence=resp.confidence,
                    fallback_used=True,
                    imagenes_paths=[]
                )

        # 3. Fallo total
        raise OCRPipelineError("Todas las estrategias OCR fallaron")

    async def _structure_steps(self, latex_raw: str) -> list[PasoMatematico]:
        """Estructura LaTeX bruto en pasos numerados (heurística simple para MVP)."""
        # Para MVP: split por líneas no vacías y numerar
        lines = [line.strip() for line in latex_raw.split("\n") if line.strip()]
        pasos = []
        for i, line in enumerate(lines, 1):
            pasos.append(PasoMatematico(numero=i, latex=line, descripcion=f"Paso {i}"))
        return pasos if pasos else [PasoMatematico(numero=1, latex=latex_raw, descripcion="Expresión completa")]
