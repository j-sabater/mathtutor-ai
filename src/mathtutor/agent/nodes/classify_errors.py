"""Nodo de clasificación de errores: Motor de reglas determinista (0 LLM)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import sympy as sp
from returns.result import Failure, Success

from mathtutor.agent.nodes.base import BaseNode
from mathtutor.agent.state import AgentState, ErrorClassification
from mathtutor.agent.tools.error_classifier import DefaultErrorClassifierEngine

if TYPE_CHECKING:
    from mathtutor.graph.repositories import EjercicioRepository


class ClassifyErrorsNode(BaseNode):
    """Clasifica errores detectados usando reglas puras Python (sin LLM)."""
    
    node_name = "classify_errors"
    
    def __init__(
        self,
        error_classifier: DefaultErrorClassifierEngine | None = None,
        exercise_repo: "EjercicioRepository | None" = None,
    ):
        super().__init__()
        self._classifier = error_classifier or DefaultErrorClassifierEngine()
        self._exercise_repo = exercise_repo
    
    async def __call__(self, state: AgentState) -> AgentState:
        self._log_start(state, validaciones=len(state.validaciones))
        self._emit_node_start(state, "Clasificando errores con motor de reglas...")
        
        if not state.validaciones:
            self._emit_node_end(state, "No hay validaciones para clasificar", {"errores": 0})
            return state.model_copy(update={
                "errores_clasificados": [],
                "current_node": "update_graph"
            })
        
        try:
            errores_clasificados = []
            total = len([v for v in state.validaciones if not v.es_correcto])
            current = 0
            
            for validation in state.validaciones:
                if validation.es_correcto:
                    continue
                
                current += 1
                self._emit_progress(state, f"Clasificando error {current}/{total}", {
                    "paso": validation.paso_numero,
                    "tipo": validation.tipo_error,
                })
                
                # Obtener expresión esperada para este paso (desde solución canónica)
                expected_expr = await self._get_expected_expr(validation, state)
                
                # Clasificar usando motor de reglas determinista
                result = self._classifier.classify(validation, expected_expr)
                
                if isinstance(result, Success):
                    error_classification = result.unwrap()
                    errores_clasificados.append(error_classification)
                else:
                    # Fallback: error no categorizado
                    errores_clasificados.append(ErrorClassification(
                        patron_codigo="ERR-UNCATEGORIZED",
                        paso=validation.paso_numero,
                        confianza=0.5,
                        es_nueva_instancia=True
                    ))
            
            self._emit_node_end(state, "Clasificación completada", {
                "errores_detectados": len(errores_clasificados),
                "patrones": [e.patron_codigo for e in errores_clasificados],
            })
            
            return state.model_copy(update={
                "errores_clasificados": errores_clasificados,
                "current_node": "update_graph"
            })
            
        except Exception as e:
            self._log_error(state, e)
            self._emit_error(state, f"Error en clasificación: {e}", e)
            return state.model_copy(update={"error": f"Error en clasificación: {e}", "current_node": "classify_errors"})
    
    async def _get_expected_expr(self, validation, state: AgentState) -> sp.Expr:
        """Obtiene la expresión SymPy esperada para comparar con la del alumno."""
        # Para MVP: construir expresión esperada básica
        # En implementación completa, vendría de ejercicio.solucion_canonica
        
        try:
            import latex2sympy2 as l2s
            # Si hay LaTeX corregido por humano, usarlo como referencia
            if state.ocr_corrected_latex:
                return l2s.latex2sympy(state.ocr_corrected_latex)
            # Si no, usar la expresión normalizada del paso
            return sp.sympify(validation.expresion_sympy)
        except Exception:
            # Fallback: expresión simbólica genérica
            return sp.Symbol('x')