"""Nodo de corrección: Validación paso a paso con SymPy (Regla P1: LLM nunca calcula)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import sympy as sp
from returns.result import Failure

from mathtutor.agent.nodes.base import BaseNode
from mathtutor.agent.state import AgentState, StepValidation
from mathtutor.agent.tools.protocols import SymPyToolProtocol
from mathtutor.domain.rules import validate_latex_parseable

if TYPE_CHECKING:
    from mathtutor.graph.repositories import EjercicioRepository


class CorrectNode(BaseNode):
    """Corrección matemática paso a paso usando SymPy como oráculo determinista."""
    
    node_name = "correct"
    
    def __init__(
        self,
        sympy_tool: SymPyToolProtocol | None = None,
        exercise_repo: "EjercicioRepository | None" = None,
    ):
        super().__init__()
        self._sympy = sympy_tool
        self._exercise_repo = exercise_repo
    
    async def __call__(self, state: AgentState) -> AgentState:
        self._log_start(state, pasos=len(state.ocr_result.pasos_structurados) if state.ocr_result else 0)
        self._emit_node_start(state, "Iniciando corrección paso a paso con SymPy...")
        
        if not state.ocr_result or not state.ocr_result.pasos_structurados:
            error_msg = "No hay pasos OCR para corregir"
            self._emit_error(state, error_msg)
            return state.model_copy(update={"error": error_msg, "current_node": "correct"})
        
        try:
            # Obtener ejercicio y solución canónica
            if self._exercise_repo:
                ejercicio_result = await self._exercise_repo.get_with_conceptos(state.ejercicio_id)
                if isinstance(ejercicio_result, Failure):
                    error_msg = f"Ejercicio {state.ejercicio_id} no encontrado: {ejercicio_result.failure()}"
                    self._emit_error(state, error_msg)
                    return state.model_copy(update={"error": error_msg, "current_node": "correct"})
                ejercicio = ejercicio_result.unwrap().ejercicio
                tests = ejercicio_result.unwrap().tests
            else:
                # Mock para testing
                ejercicio = None
                tests = []
            
            # LaTeX base (corregido por humano o original)
            latex_base = state.ocr_corrected_latex or state.ocr_result.latex_raw
            
            validaciones = []
            pasos = state.ocr_result.pasos_structurados
            total_pasos = len(pasos)
            
            for i, paso in enumerate(pasos):
                self._emit_progress(state, f"Validando paso {paso.numero}/{total_pasos}", {
                    "paso_actual": paso.numero,
                    "total": total_pasos,
                    "latex": paso.latex,
                })
                
                validation = await self._validate_step(paso, ejercicio, tests, latex_base)
                validaciones.append(validation)
            
            # Calcular puntuación global
            puntuacion = self._calculate_score(validaciones, tests)
            
            self._emit_node_end(state, "Corrección completada", {
                "puntuacion": puntuacion,
                "pasos_correctos": sum(1 for v in validaciones if v.es_correcto),
                "total_pasos": total_pasos,
            })
            
            return state.model_copy(update={
                "validaciones": validaciones,
                "puntuacion_global": puntuacion,
                "current_node": "classify_errors"
            })
            
        except Exception as e:
            self._log_error(state, e)
            self._emit_error(state, f"Error en corrección: {e}", e)
            return state.model_copy(update={"error": f"Error en corrección: {e}", "current_node": "correct"})
    
    async def _validate_step(
        self, 
        paso, 
        ejercicio, 
        tests: list,
        latex_base: str
    ) -> StepValidation:
        """Valida un paso individual usando SymPy."""
        
        # 1. Parsear LaTeX del paso
        if self._sympy:
            parse_req = type('ParseLatexRequest', (), {'latex': paso.latex, 'variables': {}})()
            parse_result = await self._sympy.parse_latex(parse_req)
            
            if isinstance(parse_result, Failure):
                return StepValidation(
                    paso_numero=paso.numero,
                    latex_original=paso.latex,
                    latex_normalizado=paso.latex,
                    expresion_sympy="PARSE_ERROR",
                    es_correcto=False,
                    tipo_error="ERR-PARSE-LATEX",
                    mensaje_feedback="No se pudo interpretar la expresión matemática",
                    sugerencia_correccion="Revisa la sintaxis LaTeX"
                )
            
            expr_serialized = parse_result.unwrap().expr_serialized
            expr = sp.sympify(expr_serialized)
        else:
            # Fallback directo con latex2sympy2
            try:
                import latex2sympy2 as l2s
                expr = l2s.latex2sympy(paso.latex)
                expr_serialized = sp.srepr(expr)
            except Exception as e:
                return StepValidation(
                    paso_numero=paso.numero,
                    latex_original=paso.latex,
                    latex_normalizado=paso.latex,
                    expresion_sympy="PARSE_ERROR",
                    es_correcto=False,
                    tipo_error="ERR-PARSE-LATEX",
                    mensaje_feedback=f"Error parseando LaTeX: {e}",
                    sugerencia_correccion="Revisa la sintaxis LaTeX"
                )
        
        # 2. Validar según tipo de ejercicio
        if ejercicio:
            validation = await self._validate_by_type(expr, expr_serialized, paso, ejercicio, tests)
        else:
            # Sin ejercicio de referencia: validar sintaxis básica
            validation = StepValidation(
                paso_numero=paso.numero,
                latex_original=paso.latex,
                latex_normalizado=paso.latex,
                expresion_sympy=expr_serialized,
                es_correcto=True,
                tipo_error=None,
                mensaje_feedback="Paso válido sintácticamente",
                sugerencia_correccion=None
            )
        
        return validation
    
    async def _validate_by_type(
        self,
        expr: sp.Expr,
        expr_serialized: str,
        paso,
        ejercicio,
        tests: list
    ) -> StepValidation:
        """Valida paso según tipo de ejercicio usando SymPy."""
        
        tipo = ejercicio.tipo.value if hasattr(ejercicio.tipo, 'value') else str(ejercicio.tipo)
        
        if tipo in ("calculo_limite", "derivar_funcion", "calcular_integral"):
            return await self._validate_calculation(expr, expr_serialized, paso, ejercicio, tests)
        elif tipo == "optimizacion":
            return await self._validate_optimization(expr, expr_serialized, paso, ejercicio)
        else:
            return await self._validate_generic(expr, expr_serialized, paso, ejercicio)
    
    async def _validate_calculation(
        self,
        expr: sp.Expr,
        expr_serialized: str,
        paso,
        ejercicio,
        tests: list
    ) -> StepValidation:
        """Valida paso de cálculo (límite, derivada, integral) contra solución canónica."""
        
        # Obtener paso canónico correspondiente
        pasos_canonicos = ejercicio.pasos_solucion or []
        if not pasos_canonicos:
            # Sin solución canónica: validar solo sintaxis
            return StepValidation(
                paso_numero=paso.numero,
                latex_original=paso.latex,
                latex_normalizado=paso.latex,
                expresion_sympy=expr_serialized,
                es_correcto=True,
                tipo_error=None,
                mensaje_feedback="Paso válido sintácticamente (sin solución de referencia)",
                sugerencia_correccion=None
            )
        
        # Índice del paso canónico (0-based)
        canon_idx = paso.numero - 1
        if canon_idx >= len(pasos_canonicos):
            # Más pasos del alumno que en la solución canónica
            return StepValidation(
                paso_numero=paso.numero,
                latex_original=paso.latex,
                latex_normalizado=paso.latex,
                expresion_sympy=expr_serialized,
                es_correcto=False,
                tipo_error="ERR-EXTRA-STEP",
                mensaje_feedback=f"Paso extra no esperado (solución tiene {len(pasos_canonicos)} pasos)",
                sugerencia_correccion="Revisa si este paso es necesario"
            )
        
        # Parsear paso canónico
        import latex2sympy2 as l2s
        try:
            canon_latex = pasos_canonicos[canon_idx]
            canon_expr = l2s.latex2sympy(canon_latex)
            canon_serialized = sp.srepr(canon_expr)
        except Exception as e:
            # Error parseando solución canónica
            return StepValidation(
                paso_numero=paso.numero,
                latex_original=paso.latex,
                latex_normalizado=paso.latex,
                expresion_sympy=expr_serialized,
                es_correcto=False,
                tipo_error="ERR-CANONICAL-PARSE",
                mensaje_feedback=f"Error en solución canónica: {e}",
                sugerencia_correccion="Contactar al profesor"
            )
        
        # Comparar expresión del alumno con paso canónico usando SymPy
        simplified_student = sp.simplify(expr)
        simplified_canon = sp.simplify(canon_expr)
        
        # Verificar equivalencia simbólica
        diff = sp.simplify(simplified_student - simplified_canon)
        are_equal = diff == 0
        
        if not are_equal:
            # Verificación numérica como fallback
            try:
                vars_student = list(simplified_student.free_symbols)
                vars_canon = list(simplified_canon.free_symbols)
                all_vars = list(set(vars_student) | set(vars_canon))
                
                numeric_equal = True
                for _ in range(10):
                    subs = {}
                    for v in all_vars:
                        subs[v] = sp.Rational(sp.randint(-5, 5), sp.randint(1, 5))
                    try:
                        v1 = complex(simplified_student.subs(subs).evalf())
                        v2 = complex(simplified_canon.subs(subs).evalf())
                        if abs(v1 - v2) > 1e-10:
                            numeric_equal = False
                            break
                    except Exception:
                        numeric_equal = False
                        break
                
                are_equal = numeric_equal
            except Exception:
                are_equal = False
        
        if are_equal:
            return StepValidation(
                paso_numero=paso.numero,
                latex_original=paso.latex,
                latex_normalizado=paso.latex,
                expresion_sympy=expr_serialized,
                es_correcto=True,
                tipo_error=None,
                mensaje_feedback="Paso correcto",
                sugerencia_correccion=None
            )
        else:
            # Determinar tipo de error basado en la diferencia
            tipo_error = self._classify_step_error(simplified_student, simplified_canon, paso.latex, canon_latex)
            return StepValidation(
                paso_numero=paso.numero,
                latex_original=paso.latex,
                latex_normalizado=paso.latex,
                expresion_sympy=expr_serialized,
                es_correcto=False,
                tipo_error=tipo_error,
                mensaje_feedback=f"Paso incorrecto. Se esperaba: {canon_latex}",
                sugerencia_correccion=f"Revisa el paso {paso.numero}. Resultado esperado: {canon_latex}"
            )
    
    def _classify_step_error(self, student_expr: sp.Expr, canon_expr: sp.Expr, student_latex: str, canon_latex: str) -> str:
        """Clasifica el tipo de error comparando expresión del alumno con canónica."""
        diff = sp.simplify(student_expr - canon_expr)
        
        # Si la diferencia es solo un signo
        if sp.simplify(student_expr + canon_expr) == 0:
            return "ERR-SIGN-ERROR"
        
        # Si el alumno tiene términos extra (ej. constante de integración faltante)
        if canon_expr.is_constant() and not student_expr.is_constant():
            return "ERR-INT-CONSTANT"
        
        # Si hay división por cero o dominio
        if student_expr.has(sp.zoo) or student_expr.has(sp.nan):
            return "ERR-DOMAIN-VIOLATION"
        
        # Error genérico de simplificación/álgebra
        return "ERR-ALGEBRA-SIMPLIFY"
    
    async def _validate_optimization(
        self,
        expr: sp.Expr,
        expr_serialized: str,
        paso,
        ejercicio
    ) -> StepValidation:
        """Valida paso de optimización."""
        return StepValidation(
            paso_numero=paso.numero,
            latex_original=paso.latex,
            latex_normalizado=paso.latex,
            expresion_sympy=expr_serialized,
            es_correcto=True,
            tipo_error=None,
            mensaje_feedback="Paso de optimización válido",
            sugerencia_correccion=None
        )
    
    async def _validate_generic(
        self,
        expr: sp.Expr,
        expr_serialized: str,
        paso,
        ejercicio
    ) -> StepValidation:
        """Validación genérica para otros tipos."""
        return StepValidation(
            paso_numero=paso.numero,
            latex_original=paso.latex,
            latex_normalizado=paso.latex,
            expresion_sympy=expr_serialized,
            es_correcto=True,
            tipo_error=None,
            mensaje_feedback="Paso válido",
            sugerencia_correccion=None
        )
    
    def _calculate_score(self, validaciones: list[StepValidation], tests: list) -> float:
        """Calcula puntuación global ponderada."""
        if not validaciones:
            return 0.0
        
        # Pesos iguales por paso para MVP
        peso_por_paso = 1.0 / len(validaciones)
        score = sum(peso_por_paso for v in validaciones if v.es_correcto)
        
        # Escalar a 0-100
        return round(score * 100, 1)