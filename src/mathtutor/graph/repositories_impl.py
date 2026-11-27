"""Implementaciones concretas de repositorios Neo4j (Repository Pattern)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from dataclasses import dataclass

from neo4j import AsyncTransaction, Record

from mathtutor.graph.session import get_session_manager
from mathtutor.graph.queries import get_query, CYPHER_QUERIES
from mathtutor.graph.mappers import (
    map_node_to_concepto,
    map_node_to_ejercicio,
    map_node_to_intento,
    map_node_to_patron,
    map_test_relation,
    map_mastery_relation,
    map_has_error_relation,
    map_recommends_relation,
)
from mathtutor.graph.repositories import (
    ConceptoRepository,
    EjercicioRepository,
    IntentoRepository,
    PatronErrorRepository,
    MasteryRepository,
    RecommendationRepository,
    SesionRepository,
    GraphError,
    TestRelationDTO,
    EjercicioWithConceptos,
    PatronErrorRefDTO,
    StudentProfile,
    ConceptoWithPrereqs,
)
from mathtutor.domain.entities import (
    Concepto,
    Ejercicio,
    Intento,
    PatronDeError,
    User,
    SesionEstudio,
    MasteryLevel,
    HasErrorRelation,
    RecommendsRelation,
    BloqueConcepto,
    TipoEjercicio,
    EstadoIntento,
    FuenteEjercicio,
    TipoPrerequisito,
    RolUsuario,
    RazonRecomendacion,
    TestRelation,
)
from returns.result import Result, Success, Failure


@dataclass
class Neo4jRepositories(
    ConceptoRepository,
    EjercicioRepository,
    IntentoRepository,
    PatronErrorRepository,
    MasteryRepository,
    RecommendationRepository,
    SesionRepository,
):
    """Implementación unificada de todos los repositorios usando Neo4j."""

    tx: AsyncTransaction

    # ── Helpers ─────────────────────────────────────────────────────────────

    async def _execute(self, query: str, params: dict[str, Any] | None = None) -> list[Record]:
        """Ejecuta query y retorna records."""
        result = await self.tx.run(query, params or {})
        return await result.data()

    async def _execute_single(self, query: str, params: dict[str, Any] | None = None) -> Record | None:
        """Ejecuta query y retorna un solo record o None."""
        records = await self._execute(query, params)
        return records[0] if records else None

    def _wrap_result(self, record: Record | None, mapper, error_msg: str = "No encontrado") -> Result[Any, GraphError]:
        """Wrapper común para mapear record a entidad."""
        if record is None:
            return Failure(GraphError(code="NOT_FOUND", message=error_msg, operation="read"))
        try:
            return Success(mapper(record))
        except Exception as e:
            return Failure(GraphError(code="MAPPING_ERROR", message=str(e), operation="map"))

    # ── ConceptoRepository ──────────────────────────────────────────────────

    async def get_by_codigo(self, codigo: str) -> Result[Concepto, GraphError]:
        query = get_query("conceptos", "read_by_codigo")
        record = await self._execute_single(query, {"codigo": codigo})
        return self._wrap_result(record, map_node_to_concepto, f"Concepto {codigo} no encontrado")

    async def get_by_id(self, id: str) -> Result[Concepto, GraphError]:
        query = get_query("conceptos", "read_by_id")
        record = await self._execute_single(query, {"id": id})
        return self._wrap_result(record, map_node_to_concepto, f"Concepto {id} no encontrado")

    async def get_all(self) -> Result[list[Concepto], GraphError]:
        query = get_query("conceptos", "read_all")
        records = await self._execute(query)
        return Success([map_node_to_concepto(r) for r in records])

    async def get_by_bloque(self, bloque: BloqueConcepto) -> Result[list[Concepto], GraphError]:
        query = get_query("conceptos", "read_by_bloque")
        records = await self._execute(query, {"bloque": bloque.value})
        return Success([map_node_to_concepto(r) for r in records])

    async def get_with_prereqs(self, codigo: str) -> Result[ConceptoWithPrereqs, GraphError]:
        query = get_query("conceptos", "read_with_prereqs")
        record = await self._execute_single(query, {"codigo": codigo})
        if record is None:
            return Failure(GraphError(code="NOT_FOUND", message=f"Concepto {codigo} no encontrado", operation="read"))

        data = dict(record)
        concepto = map_node_to_concepto(data.get("c", data))
        prerequisitos = [map_node_to_concepto({"c": p}) for p in data.get("prerequisitos", [])]
        dependientes = [map_node_to_concepto({"c": d}) for d in data.get("dependientes", [])]
        return Success(ConceptoWithPrereqs(concepto=concepto, prerequisitos=prerequisitos, dependientes=dependientes))

    async def create(self, concepto: Concepto) -> Result[Concepto, GraphError]:
        query = get_query("conceptos", "create")
        params = {
            "id": concepto.id,
            "codigo": concepto.codigo,
            "nombre": concepto.nombre,
            "bloque": concepto.bloque.value,
            "nivel": concepto.nivel,
            "descripcion": concepto.descripcion,
            "latex_definicion": concepto.latex_definicion,
            "prerequisitos_codigos": concepto.prerequisitos_codigos,
        }
        record = await self._execute_single(query, params)
        return self._wrap_result(record, map_node_to_concepto, "Error creando concepto")

    async def update(self, concepto: Concepto) -> Result[Concepto, GraphError]:
        query = get_query("conceptos", "update")
        params = {
            "id": concepto.id,
            "props": {
                "nombre": concepto.nombre,
                "descripcion": concepto.descripcion,
                "latex_definicion": concepto.latex_definicion,
                "nivel": concepto.nivel,
                "prerequisitos_codigos": concepto.prerequisitos_codigos,
            }
        }
        record = await self._execute_single(query, params)
        return self._wrap_result(record, map_node_to_concepto, "Error actualizando concepto")

    async def delete(self, codigo: str) -> Result[None, GraphError]:
        query = get_query("conceptos", "delete")
        await self._execute(query, {"codigo": codigo})
        return Success(None)

    async def add_prerequisite(
        self, from_codigo: str, to_codigo: str, tipo: TipoPrerequisito, peso: float
    ) -> Result[None, GraphError]:
        query = get_query("conceptos", "add_prerequisite")
        await self._execute(query, {"from_codigo": from_codigo, "to_codigo": to_codigo, "tipo": tipo.value, "peso": peso})
        return Success(None)

    async def remove_prerequisite(self, from_codigo: str, to_codigo: str) -> Result[None, GraphError]:
        query = get_query("conceptos", "remove_prerequisite")
        await self._execute(query, {"from_codigo": from_codigo, "to_codigo": to_codigo})
        return Success(None)

    # ── EjercicioRepository ─────────────────────────────────────────────────

    async def get_by_id(self, id: str) -> Result[Ejercicio, GraphError]:
        query = get_query("ejercicios", "read_by_id")
        record = await self._execute_single(query, {"id": id})
        return self._wrap_result(record, map_node_to_ejercicio, f"Ejercicio {id} no encontrado")

    async def get_with_conceptos(self, id: str) -> Result[EjercicioWithConceptos, GraphError]:
        query = get_query("ejercicios", "read_with_conceptos")
        record = await self._execute_single(query, {"id": id})
        if record is None:
            return Failure(GraphError(code="NOT_FOUND", message=f"Ejercicio {id} no encontrado", operation="read"))

        data = dict(record)
        ejercicio = map_node_to_ejercicio(data.get("e", data))
        tests = [map_test_relation({"r": t, "c": t.get("concepto", {})}) for t in data.get("tests", [])]
        return Success(EjercicioWithConceptos(ejercicio=ejercicio, tests=tests))

    async def get_by_tipo_dificultad(
        self, tipo: TipoEjercicio, dificultad: int | None = None
    ) -> Result[list[Ejercicio], GraphError]:
        query = get_query("ejercicios", "read_by_tipo_dificultad")
        params = {"tipo": tipo.value, "dificultad": dificultad, "limit": 100}
        records = await self._execute(query, params)
        return Success([map_node_to_ejercicio(r) for r in records])

    async def create(
        self,
        enunciado_latex: str,
        enunciado_texto: str,
        tipo: TipoEjercicio,
        dificultad: int,
        tiempo_estimado: int,
        fuente: FuenteEjercicio,
        solucion_canonica_latex: str | None,
        pasos_solucion: list[str],
        metadata_json: str,
        concepto_codigos: list[str],
        pesos: list[float],
        principales: list[bool],
    ) -> Result[str, GraphError]:
        from mathtutor.domain.entities import generate_id
        ejercicio_id = generate_id()

        query = get_query("ejercicios", "create")
        params = {
            "id": ejercicio_id,
            "enunciado_latex": enunciado_latex,
            "enunciado_texto": enunciado_texto,
            "tipo": tipo.value,
            "dificultad": dificultad,
            "tiempo_estimado": tiempo_estimado,
            "fuente": fuente.value,
            "metadata_json": metadata_json,
            "solucion_canonica_latex": solucion_canonica_latex,
            "pasos_solucion": pasos_solucion,
        }
        await self._execute(query, params)

        # Link conceptos
        link_query = get_query("ejercicios", "link_concepto")
        for codigo, peso, principal in zip(concepto_codigos, pesos, principales):
            await self._execute(link_query, {"ejercicio_id": ejercicio_id, "concepto_codigo": codigo, "peso": peso, "es_principal": principal})

        return Success(ejercicio_id)

    async def update(self, ejercicio: Ejercicio) -> Result[Ejercicio, GraphError]:
        query = get_query("ejercicios", "update")
        params = {
            "id": ejercicio.id,
            "props": {
                "enunciado_latex": ejercicio.enunciado_latex,
                "enunciado_texto": ejercicio.enunciado_texto,
                "dificultad": ejercicio.dificultad,
                "tiempo_estimado": ejercicio.tiempo_estimado,
                "metadata_json": ejercicio.metadata_json,
                "solucion_canonica_latex": ejercicio.solucion_canonica_latex,
                "pasos_solucion": ejercicio.pasos_solucion,
            }
        }
        record = await self._execute_single(query, params)
        return self._wrap_result(record, map_node_to_ejercicio, "Error actualizando ejercicio")

    async def delete(self, id: str) -> Result[None, GraphError]:
        query = get_query("ejercicios", "delete")
        await self._execute(query, {"id": id})
        return Success(None)

    async def link_concepto(
        self, ejercicio_id: str, concepto_codigo: str, peso: float, es_principal: bool
    ) -> Result[None, GraphError]:
        query = get_query("ejercicios", "link_concepto")
        await self._execute(query, {"ejercicio_id": ejercicio_id, "concepto_codigo": concepto_codigo, "peso": peso, "es_principal": es_principal})
        return Success(None)

    # ── IntentoRepository ───────────────────────────────────────────────────

    async def get_by_id(self, id: str) -> Result[Intento, GraphError]:
        query = get_query("intentos", "read_by_id")
        record = await self._execute_single(query, {"id": id})
        return self._wrap_result(record, map_node_to_intento, f"Intento {id} no encontrado")

    async def get_by_ejercicio(self, ejercicio_id: str) -> Result[list[Intento], GraphError]:
        query = get_query("intentos", "read_by_ejercicio")
        records = await self._execute(query, {"ejercicio_id": ejercicio_id})
        return Success([map_node_to_intento(r) for r in records])

    async def get_by_alumna_estado(
        self, alumna_id: str, estado: EstadoIntento | None = None
    ) -> Result[list[Intento], GraphError]:
        query = get_query("intentos", "read_by_alumna_estado")
        params = {"alumna_id": alumna_id, "estado": estado.value if estado else None, "limit": 100}
        records = await self._execute(query, params)
        return Success([map_node_to_intento(r) for r in records])

    async def create(
        self,
        ejercicio_id: str,
        alumna_id: str,
        imagenes: list[str],
        latex_extraido: str,
        pasos_structurados: str,
        estado: EstadoIntento,
        puntuacion: float,
        metadatos_ocr: str,
    ) -> Result[str, GraphError]:
        from mathtutor.domain.entities import generate_id
        intento_id = generate_id()

        query = get_query("intentos", "create")
        params = {
            "id": intento_id,
            "ejercicio_id": ejercicio_id,
            "alumna_id": alumna_id,
            "imagenes": imagenes,
            "latex_extraido": latex_extraido,
            "pasos_structurados": pasos_structurados,
            "estado": estado.value,
            "puntuacion": puntuacion,
            "metadatos_ocr": metadatos_ocr,
        }
        await self._execute(query, params)

        # Link a ejercicio y usuario
        await self._execute(get_query("intentos", "link_exercise"), {"ejercicio_id": ejercicio_id, "intento_id": intento_id, "orden": 1})
        await self._execute(get_query("intentos", "link_user"), {"intento_id": intento_id, "alumna_id": alumna_id})

        return Success(intento_id)

    async def update_estado(self, intento_id: str, estado: EstadoIntento) -> Result[None, GraphError]:
        query = get_query("intentos", "update_estado")
        await self._execute(query, {"id": intento_id, "estado": estado.value})
        return Success(None)

    async def update_correccion(
        self, intento_id: str, puntuacion: float, corregido_at: datetime
    ) -> Result[None, GraphError]:
        query = get_query("intentos", "update_correccion")
        await self._execute(query, {"id": intento_id, "puntuacion": puntuacion})
        return Success(None)

    async def link_session(self, intento_id: str, sesion_id: str, orden: int) -> Result[None, GraphError]:
        query = get_query("intentos", "link_session")
        await self._execute(query, {"intento_id": intento_id, "sesion_id": sesion_id, "orden": orden})
        return Success(None)

    async def delete(self, intento_id: str) -> Result[None, GraphError]:
        query = get_query("intentos", "delete")
        await self._execute(query, {"intento_id": intento_id})
        return Success(None)

    # ── PatronErrorRepository ───────────────────────────────────────────────

    async def get_by_codigo(self, codigo: str) -> Result[PatronDeError, GraphError]:
        query = get_query("patrones", "read_by_codigo")
        record = await self._execute_single(query, {"codigo": codigo})
        return self._wrap_result(record, map_node_to_patron, f"Patrón {codigo} no encontrado")

    async def get_by_concepto(self, concepto_codigo: str) -> Result[list[PatronDeError], GraphError]:
        query = get_query("patrones", "read_by_concepto")
        records = await self._execute(query, {"concepto_codigo": concepto_codigo})
        return Success([map_node_to_patron(r) for r in records])

    async def get_all(self) -> Result[list[PatronDeError], GraphError]:
        query = get_query("patrones", "read_all")
        records = await self._execute(query)
        return Success([map_node_to_patron(r) for r in records])

    async def create(
        self,
        codigo: str,
        nombre: str,
        descripcion: str,
        concepto_codigo: str,
        severidad: int,
        ejemplo_latex: str,
        correccion_latex: str,
    ) -> Result[PatronDeError, GraphError]:
        from mathtutor.domain.entities import generate_id
        patron_id = generate_id()

        query = get_query("patrones", "create")
        params = {
            "id": patron_id,
            "codigo": codigo,
            "nombre": nombre,
            "descripcion": descripcion,
            "concepto_codigo": concepto_codigo,
            "severidad": severidad,
            "ejemplo_latex": ejemplo_latex,
            "correccion_latex": correccion_latex,
        }
        record = await self._execute_single(query, params)
        return self._wrap_result(record, map_node_to_patron, "Error creando patrón")

    async def increment_frecuencia(self, codigo: str) -> Result[int, GraphError]:
        query = get_query("patrones", "update_frequency")
        record = await self._execute_single(query, {"codigo": codigo})
        if record is None:
            return Failure(GraphError(code="NOT_FOUND", message=f"Patrón {codigo} no encontrado", operation="update"))
        return Success(record.get("nueva_frecuencia", 0))

    async def link_intento_error(
        self, intento_id: str, patron_codigo: str, paso: int, confianza: float
    ) -> Result[None, GraphError]:
        query = get_query("patrones", "link_intento_error")
        await self._execute(query, {"intento_id": intento_id, "patron_codigo": patron_codigo, "paso": paso, "confianza": confianza})
        return Success(None)

    async def unlink_intento_error(
        self, intento_id: str, patron_codigo: str
    ) -> Result[None, GraphError]:
        query = get_query("patrones", "unlink_intento_error")
        await self._execute(query, {"intento_id": intento_id, "patron_codigo": patron_codigo})
        return Success(None)

    async def get_errores_intento(self, intento_id: str) -> Result[list[PatronErrorRefDTO], GraphError]:
        query = get_query("patrones", "get_errores_intento")
        records = await self._execute(query, {"intento_id": intento_id})
        return Success([
            PatronErrorRefDTO(
                codigo=r["patron_codigo"],
                nombre=r["patron_nombre"],
                severidad=r["severidad"],
                paso=r["paso"],
                confianza=r["confianza"],
            )
            for r in records
        ])

    # ── MasteryRepository ───────────────────────────────────────────────────

    async def get_mastery(self, alumna_id: str, concepto_codigo: str) -> Result[float | None, GraphError]:
        query = get_query("mastery", "get_mastery")
        record = await self._execute_single(query, {"alumna_id": alumna_id, "concepto_codigo": concepto_codigo})
        if record is None:
            return Success(None)
        return Success(record.get("nivel", 0.0))

    async def get_all_mastery(self, alumna_id: str) -> Result[dict[str, float], GraphError]:
        query = get_query("mastery", "get_all_mastery")
        records = await self._execute(query, {"alumna_id": alumna_id})
        return Success({r["concepto_codigo"]: r["nivel"] for r in records})

    async def update_mastery_ewma(
        self, alumna_id: str, concepto_codigo: str, score: float, alpha: float = 0.3
    ) -> Result[float, GraphError]:
        query = get_query("mastery", "update_mastery_ewma")
        record = await self._execute_single(query, {"alumna_id": alumna_id, "concepto_codigo": concepto_codigo, "nuevo_nivel": score, "alpha": alpha, "es_correcto": score >= 0.5})
        if record is None:
            return Failure(GraphError(code="NOT_FOUND", message=f"Mastery no encontrado", operation="update"))
        return Success(record.get("nuevo_nivel", 0.0))

    async def update_mastery_fields(
        self,
        alumna_id: str,
        concepto_codigo: str,
        nivel: float,
        intentos_totales: int,
        aciertos_consecutivos: int,
    ) -> Result[None, GraphError]:
        query = get_query("mastery", "update_mastery_fields")
        await self._execute(query, {
            "alumna_id": alumna_id,
            "concepto_codigo": concepto_codigo,
            "nivel": nivel,
            "intentos_totales": intentos_totales,
            "aciertos_consecutivos": aciertos_consecutivos,
        })
        return Success(None)

    # ── RecommendationRepository ────────────────────────────────────────────

    async def get_student_profile(self, alumna_id: str) -> Result[StudentProfile, GraphError]:
        query = get_query("recommendations", "get_student_profile")
        record = await self._execute_single(query, {"alumna_id": alumna_id})
        if record is None:
            return Failure(GraphError(code="NOT_FOUND", message=f"Alumna {alumna_id} no encontrada", operation="read"))

        data = dict(record)
        profile = data.get("profile", {})
        return Success(StudentProfile(
            alumna_id=profile.get("alumna_id", alumna_id),
            mastery=profile.get("mastery", {}),
            errores_recientes=profile.get("errores_recientes", []),
            racha_aciertos=profile.get("racha_aciertos", 0),
            prerequisitos_faltantes=profile.get("prerequisitos_faltantes", {}),
        ))

    async def generate_recommendations(
        self, alumna_id: str, limit: int = 5
    ) -> Result[list[Ejercicio], GraphError]:
        # This would need weak_conceptos passed in; for now delegate to profile
        profile_result = await self.get_student_profile(alumna_id)
        if isinstance(profile_result, Failure):
            return Failure(profile_result.error())

        profile = profile_result.unwrap()
        weak_conceptos = list(profile.mastery.keys())[:5] if profile.mastery else []

        query = get_query("recommendations", "get_recommendations_for_alumna")
        records = await self._execute(query, {"alumna_id": alumna_id, "weak_conceptos": weak_conceptos, "limit": limit})
        return Success([map_node_to_ejercicio(r.get("e", r)) for r in records])

    async def link_recommendation(
        self, concepto_codigo: str, ejercicio_id: str, razon: RazonRecomendacion, prioridad: int
    ) -> Result[None, GraphError]:
        query = get_query("recommendations", "link_recommendation")
        await self._execute(query, {"concepto_codigo": concepto_codigo, "ejercicio_id": ejercicio_id, "razon": razon.value, "prioridad": prioridad})
        return Success(None)

    async def unlink_recommendation(
        self, concepto_codigo: str, ejercicio_id: str
    ) -> Result[None, GraphError]:
        query = get_query("recommendations", "delete_recommendation")
        await self._execute(query, {"concepto_codigo": concepto_codigo, "ejercicio_id": ejercicio_id})
        return Success(None)

    async def get_recommendations_for_concepto(
        self, concepto_codigo: str
    ) -> Result[list[Ejercicio], GraphError]:
        query = get_query("recommendations", "get_recommendations_for_concepto")
        records = await self._execute(query, {"concepto_codigo": concepto_codigo, "limit": 20})
        return Success([map_node_to_ejercicio(r.get("e", r)) for r in records])

    # ── SesionRepository ────────────────────────────────────────────────────

    async def create(
        self, alumna_id: str, inicio: datetime
    ) -> Result[str, GraphError]:
        from mathtutor.domain.entities import generate_id
        sesion_id = generate_id()

        query = get_query("sesiones", "create")
        params = {"id": sesion_id, "alumna_id": alumna_id, "inicio": inicio.isoformat()}
        await self._execute(query, params)

        await self._execute(get_query("sesiones", "link_user"), {"sesion_id": sesion_id, "alumna_id": alumna_id})

        return Success(sesion_id)

    async def close(self, sesion_id: str, fin: datetime, ejercicios_count: int, score_promedio: float) -> Result[None, GraphError]:
        query = get_query("sesiones", "close")
        await self._execute(query, {"id": sesion_id, "fin": fin.isoformat(), "ejercicios_count": ejercicios_count, "score_promedio": score_promedio})
        return Success(None)

    async def get_by_id(self, id: str) -> Result[SesionEstudio, GraphError]:
        query = get_query("sesiones", "read_by_id")
        record = await self._execute_single(query, {"id": id})
        return self._wrap_result(record, map_node_to_sesion, f"Sesión {id} no encontrada")

    async def delete(self, id: str) -> Result[None, GraphError]:
        query = get_query("sesiones", "delete")
        await self._execute(query, {"id": id})
        return Success(None)


# ── Factory ────────────────────────────────────────────────────────────────

async def create_repositories(tx: AsyncTransaction) -> Neo4jRepositories:
    """Factory para crear repositorios con transacción inyectada."""
    return Neo4jRepositories(tx=tx)


async def get_graph_repository() -> Neo4jRepositories:
    """Dependency para FastAPI - crea repositorios con transacción propia."""
    manager = get_session_manager()
    session = manager.driver.session()
    tx = await session.begin_transaction()
    try:
        return Neo4jRepositories(tx=tx)
    except Exception:
        await tx.rollback()
        await session.close()
        raise