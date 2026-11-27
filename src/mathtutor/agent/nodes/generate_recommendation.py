"""Nodo de generación de recomendación: Generate-Validate-Retry loop con LLM + SymPy."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from returns.result import Failure, Success

from mathtutor.agent.nodes.base import BaseNode
from mathtutor.agent.state import AgentState
from mathtutor.agent.prompts.registry import get_prompt_registry, GenerateExerciseContext
from mathtutor.domain.rules import validate_latex_parseable

if TYPE_CHECKING:
    from mathtutor.llm.protocol import LLMProtocol
    from mathtutor.agent.tools.protocols import SymPyToolProtocol
    from mathtutor.graph.repositories import GraphRepository


class GenerateRecommendationNode(BaseNode):
    """Genera ejercicio adaptado: LLM genera → SymPy valida → retry si falla (máx 3)."""
    
    node_name = "generate_recommendation"
    
    def __init__(
        self,
        llm: "LLMProtocol | None" = None,
        sympy_tool: "SymPyToolProtocol | None" = None,
        graph_repo: "GraphRepository | None" = None,
    ):
        super().__init__()
        self._llm = llm
        self._sympy = sympy_tool
        self._graph = graph_repo
        self._prompts = get_prompt_registry()
    
    async def __call__(self, state: AgentState) -> AgentState:
        self._log_start(state)
        self._emit_node_start(state, "Generando recomendación personalizada...")
        
        try:
            # 1. Obtener perfil alumna y concepto objetivo
            perfil = await self._get_student_profile(state)
            target_concept = self._select_target_concept(perfil)
            
            if not target_concept:
                self._emit_node_end(state, "No hay concepto objetivo para recomendar", {})
                return state.model_copy(update={"current_node": "done"})
            
            # 2. Bucle Generate-Validate-Retry
            for attempt in range(state.max_retries):
                self._emit_progress(state, f"Generando ejercicio (intento {attempt + 1}/{state.max_retries})", {
                    "concepto": target_concept["codigo"],
                    "intento": attempt + 1,
                })
                
                # Generar con LLM
                ejercicio_candidato = await self._generate_exercise_with_llm(state, target_concept, attempt)
                if not ejercicio_candidato:
                    continue
                
                # Validar con SymPy
                validation = await self._validate_exercise_with_sympy(ejercicio_candidato, target_concept)
                
                if isinstance(validation, Success):
                    # 3. Persistir y linkar
                    self._emit_progress(state, "Ejercicio válido, persistiendo en grafo...")
                    ejercicio_id = await self._persist_exercise(state, validation.unwrap(), target_concept)
                    
                    # 4. Generar apunte personalizado si hay patrones recurrentes
                    apunte_url = None
                    if perfil.get("patrones_recurrentes"):
                        apunte_url = await self._generate_personalized_note(perfil, target_concept)
                    
                    self._emit_node_end(state, "Recomendación generada y validada", {
                        "ejercicio_id": ejercicio_id,
                        "concepto": target_concept["codigo"],
                        "apunte": apunte_url is not None,
                    })
                    
                    return state.model_copy(update={
                        "ejercicio_recomendado_id": ejercicio_id,
                        "apunte_generado_url": apunte_url,
                        "current_node": "done"
                    })
                
                # Reintento con feedback
                self._emit_progress(state, f"Validación fallida: {validation.failure()}, reintentando...")
                state = state.model_copy(update={"retry_count": attempt + 1})
            
            # Falló tras max_retries
            error_msg = "No se pudo generar ejercicio válido tras reintentos"
            self._emit_error(state, error_msg)
            return state.model_copy(update={"error": error_msg, "current_node": "generate_recommendation"})
            
        except Exception as e:
            self._log_error(state, e)
            self._emit_error(state, f"Error generando recomendación: {e}", e)
            return state.model_copy(update={"error": f"Error generando recomendación: {e}", "current_node": "generate_recommendation"})
    
    async def _get_student_profile(self, state: AgentState) -> dict[str, Any]:
        """Obtiene perfil completo de la alumna desde grafo."""
        if self._graph:
            result = await self._graph.get_student_profile(state.alumna_id)
            if isinstance(result, Success):
                return result.unwrap().model_dump()
        
        # Mock para testing
        return {
            "alumna_id": state.alumna_id,
            "mastery": {},
            "errores_recientes": [],
            "racha_aciertos": 0,
            "patrones_recurrentes": [],
            "intentos_recientes": [],
        }
    
    def _select_target_concept(self, perfil: dict) -> dict | None:
        """Selecciona concepto objetivo: más débil con prereqs faltantes."""
        # Para MVP: primer concepto con mastery bajo
        mastery = perfil.get("mastery", {})
        if not mastery:
            return {"codigo": "LIM-01", "nombre": "Límite en un punto", "bloque": "Límites", 
                    "descripcion": "Definición formal de límite", "tipo_ejercicio": "calculo_limite"}
        
        # Ordenar por mastery ascendente
        sorted_concepts = sorted(mastery.items(), key=lambda x: x[1])
        concepto_codigo = sorted_concepts[0][0]
        
        return {
            "codigo": concepto_codigo,
            "nombre": concepto_codigo.replace("-", " ").title(),
            "bloque": "Límites",
            "descripcion": "Concepto a reforzar",
            "tipo_ejercicio": "calculo_limite",
        }
    
    async def _generate_exercise_with_llm(
        self, 
        state: AgentState, 
        target_concept: dict,
        attempt: int
    ) -> dict | None:
        """Genera ejercicio candidato usando LLM."""
        if not self._llm:
            # Mock para testing
            return {
                "enunciado_latex": r"Calcular \lim_{x \to 0} \frac{\sin(x)}{x}",
                "enunciado_texto": "Calcular el límite de sen(x)/x cuando x tiende a 0",
                "solucion_canonica_latex": "1",
                "pasos_solucion": [r"\lim_{x \to 0} \frac{\sin(x)}{x} = 1"],
                "metadata": {"tags": ["evau", "limites"]}
            }
        
        contexto = GenerateExerciseContext(
            trace_id=state.trace_id,
            alumna_id=state.alumna_id,
            ejercicio_id=state.ejercicio_id,
            concepto_codigo=target_concept["codigo"],
            concepto_nombre=target_concept["nombre"],
            concepto_bloque=target_concept["bloque"],
            concepto_descripcion=target_concept["descripcion"],
            mastery_actual=0.0,
            errores_recientes=[],
            racha_aciertos=0,
            dificultad_objetivo=2,
        )
        
        prompt = self._prompts.render("generate_exercise.j2", contexto)
        
        try:
            response = await self._llm.generate(prompt, temperature=0.7)
            return self._parse_llm_exercise(response)
        except Exception as e:
            self._logger.error("llm_generation_failed", error=str(e))
            return None
    
    def _parse_llm_exercise(self, response: str) -> dict | None:
        """Parsea respuesta JSON del LLM."""
        import json
        try:
            # Extraer JSON del response (puede venir con markdown)
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except Exception as e:
            self._logger.error("parse_llm_failed", error=str(e))
        return None
    
    async def _validate_exercise_with_sympy(
        self, 
        ejercicio: dict, 
        target_concept: dict
    ) -> "Result[dict, str]":
        """Valida ejercicio generado con SymPy: ¿tiene solución? ¿LaTeX parseable?"""
        from returns.result import Success, Failure
        
        # 1. Validar LaTeX parseable
        latex = ejercicio.get("enunciado_latex", "") or ejercicio.get("solucion_canonica_latex", "")
        validation = validate_latex_parseable(latex)
        if isinstance(validation, Failure):
            return Failure(f"LaTeX no parseable: {validation.failure()}")
        
        # 2. Validar que la solución canónica es parseable
        solucion = ejercicio.get("solucion_canonica_latex", "")
        if solucion:
            sol_validation = validate_latex_parseable(solucion)
            if isinstance(sol_validation, Failure):
                return Failure(f"Solución canónica no parseable: {sol_validation.failure()}")
        
        # 3. Validar pasos de solución si existen
        for paso in ejercicio.get("pasos_solucion", []):
            paso_validation = validate_latex_parseable(paso)
            if isinstance(paso_validation, Failure):
                return Failure(f"Paso no parseable: {paso_validation.failure()}")
        
        # 4. Si hay SymPy tool, verificar que la solución es correcta
        if self._sympy and solucion:
            # TODO: Verificar equivalencia simbólica si hay parámetros
            pass
        
        return Success(ejercicio)
    
    async def _persist_exercise(self, state: AgentState, ejercicio: dict, target_concept: dict) -> str:
        """Persiste ejercicio generado y crea link :RECOMMENDS."""
        if not self._graph:
            return f"ejercicio-gen-{state.trace_id[:8]}"
        
        result = await self._graph.create(
            enunciado_latex=ejercicio["enunciado_latex"],
            enunciado_texto=ejercicio["enunciado_texto"],
            tipo=target_concept["tipo_ejercicio"],
            dificultad=2,
            tiempo_estimado=10,
            fuente="generado_ia",
            solucion_canonica_latex=ejercicio.get("solucion_canonica_latex"),
            pasos_solucion=ejercicio.get("pasos_solucion", []),
            metadata_json="{}",
            concepto_codigos=[target_concept["codigo"]],
            pesos=[1.0],
            principales=[True],
        )
        
        if isinstance(result, Failure):
            raise RuntimeError(f"Error creando ejercicio: {result.failure()}")
        
        ejercicio_id = result.unwrap()
        
        # Link recomendación
        await self._graph.link_recommendation(
            target_concept["codigo"], ejercicio_id, "refuerzo", 1
        )
        
        return ejercicio_id
    
    async def _generate_personalized_note(self, perfil: dict, target_concept: dict) -> str | None:
        """Genera apunte personalizado (async, opcional)."""
        # TODO: Implementar con NoteGenerationWorkflow
        return None