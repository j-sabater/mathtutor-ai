"""Interfaces de repositorio (Protocol) y DTOs para Neo4j."""

from __future__ import annotations

from typing import Protocol, Annotated
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from returns.result import Result

from mathtutor.domain.entities import (
    Concepto,
    Ejercicio,
    Intento,
    PatronDeError,
    User,
    SesionEstudio,
    TestRelation,
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
)


class GraphError(BaseModel):
    """Error de operación en grafo."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    code: str
    message: str
    operation: str
    context: dict = Field(default_factory=dict)


# ── DTOs para Repositorio (separados de entidades de dominio) ─────────

class TestRelationDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    concepto: Concepto
    peso: Annotated[float, Field(ge=0.0, le=1.0)]
    es_principal: bool


class EjercicioWithConceptos(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    ejercicio: Ejercicio
    tests: list[TestRelationDTO]


class PatronErrorRefDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    codigo: str
    nombre: str
    severidad: int
    paso: int
    confianza: float


class StudentProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    alumna_id: str
    mastery: dict[str, float]  # concepto_codigo -> nivel
    errores_recientes: list[PatronErrorRefDTO]
    racha_aciertos: int
    prerequisitos_faltantes: dict[str, list[str]]


class ConceptoWithPrereqs(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    concepto: Concepto
    prerequisitos: list[Concepto]
    dependientes: list[Concepto]


# ── Repository Protocols ──────────────────────────────────────────────

class ConceptoRepository(Protocol):
    async def get_by_codigo(self, codigo: str) -> Result[Concepto, GraphError]: ...
    async def get_by_id(self, id: str) -> Result[Concepto, GraphError]: ...
    async def get_all(self) -> Result[list[Concepto], GraphError]: ...
    async def get_by_bloque(self, bloque: BloqueConcepto) -> Result[list[Concepto], GraphError]: ...
    async def get_with_prereqs(self, codigo: str) -> Result[ConceptoWithPrereqs, GraphError]: ...
    async def create(self, concepto: Concepto) -> Result[Concepto, GraphError]: ...
    async def update(self, concepto: Concepto) -> Result[Concepto, GraphError]: ...
    async def delete(self, codigo: str) -> Result[None, GraphError]: ...
    async def add_prerequisite(
        self, from_codigo: str, to_codigo: str, tipo: TipoPrerequisito, peso: float
    ) -> Result[None, GraphError]: ...
    async def remove_prerequisite(self, from_codigo: str, to_codigo: str) -> Result[None, GraphError]: ...


class EjercicioRepository(Protocol):
    async def get_by_id(self, id: str) -> Result[Ejercicio, GraphError]: ...
    async def get_with_conceptos(self, id: str) -> Result[EjercicioWithConceptos, GraphError]: ...
    async def get_by_tipo_dificultad(
        self, tipo: TipoEjercicio, dificultad: int | None = None
    ) -> Result[list[Ejercicio], GraphError]: ...
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
    ) -> Result[str, GraphError]: ...  # returns ejercicio_id
    async def update(self, ejercicio: Ejercicio) -> Result[Ejercicio, GraphError]: ...
    async def delete(self, id: str) -> Result[None, GraphError]: ...
    async def link_concepto(
        self, ejercicio_id: str, concepto_codigo: str, peso: float, es_principal: bool
    ) -> Result[None, GraphError]: ...


class IntentoRepository(Protocol):
    async def get_by_id(self, id: str) -> Result[Intento, GraphError]: ...
    async def get_by_ejercicio(self, ejercicio_id: str) -> Result[list[Intento], GraphError]: ...
    async def get_by_alumna_estado(
        self, alumna_id: str, estado: EstadoIntento | None = None
    ) -> Result[list[Intento], GraphError]: ...
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
    ) -> Result[str, GraphError]: ...  # returns intento_id
    async def update_estado(self, intento_id: str, estado: EstadoIntento) -> Result[None, GraphError]: ...
    async def update_correccion(
        self, intento_id: str, puntuacion: float, corregido_at: datetime
    ) -> Result[None, GraphError]: ...
    async def link_session(self, intento_id: str, sesion_id: str, orden: int) -> Result[None, GraphError]: ...
    async def delete(self, intento_id: str) -> Result[None, GraphError]: ...


class PatronErrorRepository(Protocol):
    async def get_by_codigo(self, codigo: str) -> Result[PatronDeError, GraphError]: ...
    async def get_by_concepto(self, concepto_codigo: str) -> Result[list[PatronDeError], GraphError]: ...
    async def get_all(self) -> Result[list[PatronDeError], GraphError]: ...
    async def create(
        self,
        codigo: str,
        nombre: str,
        descripcion: str,
        concepto_codigo: str,
        severidad: int,
        ejemplo_latex: str,
        correccion_latex: str,
    ) -> Result[PatronDeError, GraphError]: ...
    async def increment_frecuencia(self, codigo: str) -> Result[int, GraphError]: ...
    async def link_intento_error(
        self, intento_id: str, patron_codigo: str, paso: int, confianza: float
    ) -> Result[None, GraphError]: ...
    async def unlink_intento_error(
        self, intento_id: str, patron_codigo: str
    ) -> Result[None, GraphError]: ...
    async def get_errores_intento(self, intento_id: str) -> Result[list[PatronErrorRefDTO], GraphError]: ...


class MasteryRepository(Protocol):
    async def get_mastery(self, alumna_id: str, concepto_codigo: str) -> Result[float | None, GraphError]: ...
    async def get_all_mastery(self, alumna_id: str) -> Result[dict[str, float], GraphError]: ...
    async def update_mastery_ewma(
        self, alumna_id: str, concepto_codigo: str, score: float, alpha: float = 0.3
    ) -> Result[float, GraphError]: ...  # returns nuevo_nivel
    async def update_mastery_fields(
        self,
        alumna_id: str,
        concepto_codigo: str,
        nivel: float,
        intentos_totales: int,
        aciertos_consecutivos: int,
    ) -> Result[None, GraphError]: ...


class RecommendationRepository(Protocol):
    async def get_student_profile(self, alumna_id: str) -> Result[StudentProfile, GraphError]: ...
    async def generate_recommendations(
        self, alumna_id: str, limit: int = 5
    ) -> Result[list[Ejercicio], GraphError]: ...
    async def link_recommendation(
        self, concepto_codigo: str, ejercicio_id: str, razon: RazonRecomendacion, prioridad: int
    ) -> Result[None, GraphError]: ...
    async def unlink_recommendation(
        self, concepto_codigo: str, ejercicio_id: str
    ) -> Result[None, GraphError]: ...
    async def get_recommendations_for_concepto(
        self, concepto_codigo: str
    ) -> Result[list[Ejercicio], GraphError]: ...


class SesionRepository(Protocol):
    async def create(
        self, alumna_id: str, inicio: datetime
    ) -> Result[str, GraphError]: ...  # returns sesion_id
    async def close(self, sesion_id: str, fin: datetime, ejercicios_count: int, score_promedio: float) -> Result[None, GraphError]: ...
    async def get_active(self, alumna_id: str) -> Result[SesionEstudio | None, GraphError]: ...


# ── Aggregate GraphRepository (fachada unificada) ────────────────────

class GraphRepository(
    ConceptoRepository,
    EjercicioRepository,
    IntentoRepository,
    PatronErrorRepository,
    MasteryRepository,
    RecommendationRepository,
    SesionRepository,
    Protocol,
):
    """Interfaz unificada para acceso al grafo de conocimiento."""
    pass
