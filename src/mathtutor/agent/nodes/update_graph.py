"""Nodo de actualización del grafo: Transacción Saga con compensación/rollback."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from returns.result import Failure

from mathtutor.agent.nodes.base import BaseNode
from mathtutor.agent.state import AgentState, GraphUpdateResult, ErrorClassification
from mathtutor.domain.rules import validate_test_weights_sum

if TYPE_CHECKING:
    from mathtutor.graph.repositories import GraphRepository, PatronErrorRepository


class UpdateGraphNode(BaseNode):
    """Actualiza grafo de conocimiento con patrón Saga (compensación en caso de fallo)."""
    
    node_name = "update_graph"
    
    def __init__(
        self,
        graph_repo: "GraphRepository | None" = None,
        error_repo: "PatronErrorRepository | None" = None,
    ):
        super().__init__()
        self._graph = graph_repo
        self._errors = error_repo
        self._executed_steps: list[tuple[str, Any]] = []  # Para compensación
    
    async def __call__(self, state: AgentState) -> AgentState:
        self._log_start(state, errores=len(state.errores_clasificados))
        self._emit_node_start(state, "Actualizando grafo de conocimiento (Saga)...")
        self._executed_steps = []
        
        try:
            # 1. Persistir Intento (estado corregido)
            self._emit_progress(state, "Persistiendo intento corregido...")
            intento_id = await self._persist_intento(state)
            self._executed_steps.append(("delete_intento", intento_id))
            
            # 2. Para cada error clasificado: upsert PatronDeError + link :HAS_ERROR
            self._emit_progress(state, "Registrando errores detectados...")
            errores_persistidos = await self._persist_errors(state, intento_id)
            
            # 3. Actualizar Mastery Level por concepto (EWMA)
            self._emit_progress(state, "Actualizando niveles de mastery (EWMA)...")
            mastery_actualizado = await self._update_mastery(state)
            
            # 4. Generar recomendación inmediata
            self._emit_progress(state, "Generando recomendación de siguiente ejercicio...")
            recomendaciones = await self._generate_recommendations(state)
            
            self._emit_node_end(state, "Grafo actualizado correctamente", {
                "intento_id": intento_id,
                "errores_persistidos": len(errores_persistidos),
                "conceptos_actualizados": len(mastery_actualizado),
                "recomendaciones": len(recomendaciones),
            })
            
            return state.model_copy(update={
                "graph_update": GraphUpdateResult(
                    mastery_actualizado=mastery_actualizado,
                    errores_persistidos=errores_persistidos,
                    recomendaciones_creadas=recomendaciones
                ),
                "current_node": "generate_recommendation"
            })
            
        except Exception as e:
            # COMPENSACIÓN: Rollback en orden inverso
            self._emit_error(state, f"Error en actualización grafo, iniciando rollback: {e}", e)
            await self._compensate()
            raise
    
    async def _persist_intento(self, state: AgentState) -> str:
        """Persiste el intento corregido."""
        if not self._graph:
            # Mock para testing
            return f"intento-mock-{state.trace_id[:8]}"
        
        latex_final = state.ocr_corrected_latex or state.ocr_result.latex_raw
        pasos_json = "\n".join([f"{v.paso_numero}:{v.latex_original}:{v.es_correcto}" for v in state.validaciones])
        metadatos_ocr = f"strategy={state.ocr_result.strategy_used},confidence={state.ocr_result.confidence}"
        
        result = await self._graph.create_intento(
            ejercicio_id=state.ejercicio_id,
            alumna_id=state.alumna_id,
            imagenes=[],  # URLs ya guardadas en ingest
            latex_extraido=latex_final,
            pasos_structurados=pasos_json,
            estado="corregido",
            puntuacion=state.puntuacion_global or 0.0,
            metadatos_ocr=metadatos_ocr,
        )
        
        if isinstance(result, Failure):
            raise RuntimeError(f"Error creando intento: {result.failure()}")
        
        return result.unwrap()
    
    async def _persist_errors(self, state: AgentState, intento_id: str) -> list[ErrorClassification]:
        """Registra errores detectados y crea links :HAS_ERROR."""
        if not self._graph or not state.errores_clasificados:
            return []
        
        errores_persistidos = []
        
        for ec in state.errores_clasificados:
            # Verificar si ya existe patrón
            if self._errors:
                patron_result = await self._errors.get_by_codigo(ec.patron_codigo)
                es_nueva = isinstance(patron_result, Failure)
            else:
                es_nueva = True
            
            if es_nueva and self._errors:
                # Crear nuevo patrón
                concepto_codigo = self._infer_concepto_from_paso(ec.paso, state.ejercicio_id)
                await self._errors.create(
                    codigo=ec.patron_codigo,
                    nombre=self._nombre_from_codigo(ec.patron_codigo),
                    descripcion=f"Error detectado en paso {ec.paso}",
                    concepto_codigo=concepto_codigo or "DESCONOCIDO",
                    severidad=3,
                    ejemplo_latex="",
                    correccion_latex="",
                )
            
            # Link Intento -> PatronDeError
            await self._graph.link_intento_error(
                intento_id, ec.patron_codigo, ec.paso, ec.confianza
            )
            # Registrar para compensación
            self._executed_steps.append(("unlink_intento_error", (intento_id, ec.patron_codigo)))
            
            errores_persistidos.append(ec.model_copy(update={"es_nueva_instancia": es_nueva}))
        
        return errores_persistidos
    
    async def _update_mastery(self, state: AgentState) -> dict[str, float]:
        """Actualiza Mastery Level por concepto usando EWMA."""
        if not self._graph:
            return {}
        
        mastery_actualizado = {}
        
        # Obtener ejercicio con conceptos testeados
        ejercicio_result = await self._graph.get_ejercicio_with_conceptos(state.ejercicio_id)
        if isinstance(ejercicio_result, Failure):
            return mastery_actualizado
        
        tests = ejercicio_result.unwrap().tests
        
        for test_rel in tests:
            concepto = test_rel.concepto
            # Calcular score para este concepto basado en pasos relacionados
            acierto_concepto = self._compute_concept_score(concepto.codigo, state.validaciones)
            
            result = await self._graph.update_mastery_ewma(
                alumna_id=state.alumna_id,
                concepto_codigo=concepto.codigo,
                score=acierto_concepto
            )
            
            if isinstance(result, Success):
                mastery_actualizado[concepto.codigo] = result.unwrap()
        
        return mastery_actualizado
    
    def _compute_concept_score(self, concepto_codigo: str, validaciones: list) -> float:
        """Calcula score de acierto para un concepto basado en sus pasos."""
        # Para MVP: promedio simple de pasos correctos
        # En implementación completa, mapear pasos a conceptos
        if not validaciones:
            return 0.0
        correctos = sum(1 for v in validaciones if v.es_correcto)
        return correctos / len(validaciones)
    
    async def _generate_recommendations(self, state: AgentState) -> list[str]:
        """Genera recomendación de siguiente ejercicio."""
        if not self._graph:
            return []
        
        recomendaciones_result = await self._graph.generate_recommendations(state.alumna_id, limit=1)
        if isinstance(recomendaciones_result, Success):
            ejercicios = recomendaciones_result.unwrap()
            if ejercicios:
                # Registrar para compensación (necesitamos el concepto origen)
                # Para MVP, usamos el primer concepto testeado
                ejercicio_result = await self._graph.get_ejercicio_with_conceptos(state.ejercicio_id)
                if isinstance(ejercicio_result, Success):
                    tests = ejercicio_result.unwrap().tests
                    if tests:
                        concepto_codigo = tests[0].concepto.codigo
                        self._executed_steps.append(("unlink_recommendation", (concepto_codigo, ejercicios[0].id)))
            return [ej.id for ej in ejercicios]
        return []
    
    def _infer_concepto_from_paso(self, paso: int, ejercicio_id: str) -> str | None:
        """Infere concepto desde número de paso (heurística simple para MVP)."""
        # En implementación completa, consultar grafo
        return None
    
    def _nombre_from_codigo(self, codigo: str) -> str:
        """Genera nombre legible desde código de error."""
        nombres = {
            "ERR-CHAIN-RULE": "Regla de la cadena omitida",
            "ERR-SIGN-ERROR": "Error de signo",
            "ERR-LHOPITAL-MISUSE": "Mal uso de L'Hôpital",
            "ERR-LIM-INDET": "Indeterminación sin resolver",
            "ERR-INT-CONSTANT": "Constante de integración faltante",
            "ERR-ALGEBRA-SIMPLIFY": "Error de simplificación algebraica",
            "ERR-DOMAIN-VIOLATION": "Violación de dominio",
            "ERR-PARSE-LATEX": "Error de parsing LaTeX",
            "ERR-UNCATEGORIZED": "Error no categorizado",
        }
        return nombres.get(codigo, "Error desconocido")
    
    async def _compensate(self) -> None:
        """Ejecuta compensación (rollback) en orden inverso."""
        self._emit_progress(self, "Ejecutando compensación (rollback)...")
        
        for action, param in reversed(self._executed_steps):
            try:
                if action == "delete_intento" and self._graph:
                    await self._graph.delete_intento(param)
                    self._logger.info("compensate_deleted_intento", intento_id=param)
                elif action == "unlink_intento_error" and self._errors:
                    # param = (intento_id, patron_codigo)
                    await self._errors.unlink_intento_error(param[0], param[1])
                    self._logger.info("compensate_unlinked_error", intento_id=param[0], patron_codigo=param[1])
                elif action == "unlink_recommendation" and self._graph:
                    # param = (concepto_codigo, ejercicio_id)
                    await self._graph.unlink_recommendation(param[0], param[1])
                    self._logger.info("compensate_unlinked_recommendation", concepto_codigo=param[0], ejercicio_id=param[1])
            except Exception as e:
                self._logger.error("compensate_failed", action=action, param=param, error=str(e))