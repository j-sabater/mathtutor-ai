"""Nodo de ingesta: OCR híbrido + estructuración de pasos."""

from __future__ import annotations

from typing import TYPE_CHECKING

from returns.result import Failure

from mathtutor.agent.nodes.base import BaseNode
from mathtutor.agent.state import AgentState, OCRResult, PasoMatematico
from mathtutor.domain.rules import validate_latex_parseable
from mathtutor.ingestion.pipeline import OCRPipeline

if TYPE_CHECKING:
    from mathtutor.graph.repositories import EjercicioRepository


class IngestNode(BaseNode):
    """Ingesta multimodal: ejecuta OCR → estructura LaTeX en pasos → valida parseabilidad."""
    
    node_name = "ingest"
    
    def __init__(
        self,
        ocr_pipeline: OCRPipeline | None = None,
        exercise_repo: "EjercicioRepository | None" = None,
    ):
        super().__init__()
        self._ocr_pipeline = ocr_pipeline
        self._exercise_repo = exercise_repo
    
    async def __call__(self, state: AgentState) -> AgentState:
        self._log_start(state, imagenes_count=len(state.imagenes))
        self._emit_node_start(state, "Procesando imágenes con OCR híbrido...")
        
        try:
            # 1. Recuperar ejercicio para contexto
            if self._exercise_repo:
                ejercicio_result = await self._exercise_repo.get_with_conceptos(state.ejercicio_id)
                if isinstance(ejercicio_result, Failure):
                    error_msg = f"Ejercicio {state.ejercicio_id} no encontrado: {ejercicio_result.failure()}"
                    self._emit_error(state, error_msg)
                    return state.model_copy(update={"error": error_msg, "current_node": "ingest"})
                ejercicio = ejercicio_result.unwrap().ejercicio
                conceptos = [t.concepto.codigo for t in ejercicio_result.unwrap().tests]
            else:
                ejercicio = None
                conceptos = []
            
            # 2. Ejecutar pipeline OCR híbrido
            self._emit_progress(state, "Ejecutando OCR local...", {"strategy": "local"})
            
            if self._ocr_pipeline:
                ocr_result = await self._ocr_pipeline.process(
                    images=state.imagenes,
                    context={
                        "tipo": ejercicio.tipo.value if ejercicio else "desconocido",
                        "conceptos": conceptos,
                    }
                )
            else:
                # Fallback mock para testing
                ocr_result = OCRResult(
                    latex_raw=r"x^2 + 2x + 1",
                    pasos_structurados=[PasoMatematico(numero=1, latex=r"x^2 + 2x + 1")],
                    strategy_used="mock",
                    confidence=1.0,
                    fallback_used=False,
                    imagenes_paths=[]
                )
            
            # 3. Validar LaTeX parseable (RV-04)
            validation = validate_latex_parseable(ocr_result.latex_raw)
            if isinstance(validation, Failure):
                error_msg = f"LaTeX no parseable por SymPy: {validation.failure()}"
                self._emit_error(state, error_msg)
                return state.model_copy(update={"error": error_msg, "current_node": "ingest"})
            
            # 4. Estructurar en pasos si no vino del pipeline
            if not ocr_result.pasos_structurados:
                pasos = await self._structure_steps(ocr_result.latex_raw)
                ocr_result = ocr_result.model_copy(update={"pasos_structurados": pasos})
            
            self._emit_node_end(state, "OCR completado y LaTeX estructurado", {
                "strategy": ocr_result.strategy_used,
                "confidence": ocr_result.confidence,
                "pasos": len(ocr_result.pasos_structurados),
            })
            
            return state.model_copy(update={
                "ocr_result": ocr_result,
                "current_node": "review_ocr"
            })
            
        except Exception as e:
            self._log_error(state, e)
            self._emit_error(state, f"Error en ingesta: {e}", e)
            return state.model_copy(update={"error": f"Error en ingesta: {e}", "current_node": "ingest"})
    
    async def _structure_steps(self, latex_raw: str) -> list[PasoMatematico]:
        """Estructura LaTeX bruto en pasos numerados (heurística simple para MVP)."""
        lines = [line.strip() for line in latex_raw.split("\n") if line.strip()]
        pasos = []
        for i, line in enumerate(lines, 1):
            pasos.append(PasoMatematico(numero=i, latex=line, descripcion=f"Paso {i}"))
        return pasos if pasos else [PasoMatematico(numero=1, latex=latex_raw, descripcion="Expresión completa")]