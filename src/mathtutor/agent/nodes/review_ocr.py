"""Nodo de revisión humana (Human-in-the-loop): Interrupt point para aprobación/corrección de OCR."""

from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.types import Command, interrupt
from returns.result import Failure

from mathtutor.agent.nodes.base import BaseNode
from mathtutor.agent.state import AgentState, OCRResult, PasoMatematico
from mathtutor.domain.rules import validate_latex_parseable

if TYPE_CHECKING:
    pass  # No external deps needed


class ReviewOCRNode(BaseNode):
    """Human-in-the-loop: pausa ejecución → presenta LaTeX → espera aprobación/corrección del profesor."""
    
    node_name = "review_ocr"
    
    def __init__(self):
        super().__init__()
    
    async def __call__(self, state: AgentState) -> Command:
        self._log_start(state)
        self._emit_node_start(state, "Esperando revisión humana del LaTeX extraído...")
        
        if not state.ocr_result:
            error_msg = "No hay resultado OCR para revisar"
            self._emit_error(state, error_msg)
            return Command(update={"error": error_msg, "current_node": "review_ocr"})
        
        # Preparar payload para UI (LangGraph serializa estado y espera resume)
        payload = {
            "trace_id": state.trace_id,
            "latex_raw": state.ocr_result.latex_raw,
            "pasos": [p.model_dump() for p in state.ocr_result.pasos_structurados],
            "confidence": state.ocr_result.confidence,
            "strategy": state.ocr_result.strategy_used,
            "fallback_used": state.ocr_result.fallback_used,
        }
        
        self._emit_progress(state, "Presentando LaTeX para revisión...", payload)
        
        # INTERRUPT: LangGraph pausa aquí y espera resume() desde API
        human_response = interrupt(payload)
        
        # human_response = {"action": "approve" | "correct", "corrected_latex": "..."}
        action = human_response.get("action", "approve")
        
        if action == "approve":
            self._emit_node_end(state, "LaTeX aprobado por profesor", {"action": "approve"})
            return Command(update={
                "ocr_approved": True,
                "ocr_corrected_latex": None,
                "current_node": "correct"
            })
        
        elif action == "correct":
            corrected_latex = human_response.get("corrected_latex", "").strip()
            
            if not corrected_latex:
                error_msg = "LaTeX corregido vacío"
                self._emit_error(state, error_msg)
                return Command(update={
                    "error": error_msg,
                    "current_node": "review_ocr"  # Re-intent
                })
            
            # Validar LaTeX corregido por humano
            validation = validate_latex_parseable(corrected_latex)
            if isinstance(validation, Failure):
                error_msg = f"LaTeX corregido inválido: {validation.failure()}"
                self._emit_error(state, error_msg)
                return Command(update={
                    "error": error_msg,
                    "current_node": "review_ocr"  # Re-intent
                })
            
            # Re-estructurar pasos con LaTeX corregido
            pasos = await self._structure_steps(corrected_latex)
            
            self._emit_node_end(state, "LaTeX corregido por profesor y validado", {
                "action": "correct",
                "pasos": len(pasos),
            })
            
            return Command(update={
                "ocr_approved": True,
                "ocr_corrected_latex": corrected_latex,
                "ocr_result": state.ocr_result.model_copy(update={
                    "latex_raw": corrected_latex,
                    "pasos_structurados": pasos
                }),
                "current_node": "correct"
            })
        
        else:
            error_msg = f"Acción desconocida: {action}. Use 'approve' o 'correct'"
            self._emit_error(state, error_msg)
            return Command(update={"error": error_msg, "current_node": "review_ocr"})
    
    async def _structure_steps(self, latex_raw: str) -> list[PasoMatematico]:
        """Estructura LaTeX corregido en pasos."""
        lines = [line.strip() for line in latex_raw.split("\n") if line.strip()]
        pasos = []
        for i, line in enumerate(lines, 1):
            pasos.append(PasoMatematico(numero=i, latex=line, descripcion=f"Paso {i}"))
        return pasos if pasos else [PasoMatematico(numero=1, latex=latex_raw, descripcion="Expresión completa")]