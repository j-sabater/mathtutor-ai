"""Entidades de dominio puras (sin dependencias de infraestructura)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Annotated, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.types import UUID4

from mathtutor.domain.value_objects import LatexString


class BloqueConcepto(str, Enum):
    """Bloques curriculares de Matemáticas II."""

    LIMITES = "Límites"
    DERIVADAS = "Derivadas"
    INTEGRALES = "Integrales"
    OPTIMIZACION = "Optimización"
    CONTINUIDAD = "Continuidad"


class TipoEjercicio(str, Enum):
    """Tipos de ejercicios soportados."""

    CALCULO_LIMITE = "calculo_limite"
    DERIVAR_FUNCION = "derivar_funcion"
    CALCULAR_INTEGRAL = "calcular_integral"
    OPTIMIZACION = "optimizacion"
    ESTUDIO_FUNCION = "estudio_funcion"


class EstadoIntento(str, Enum):
    """Estados del intento de resolución."""

    PENDIENTE = "pendiente"
    CORRIGIENDO = "corrigiendo"
    CORREGIDO = "corregido"
    ERROR_OCR = "error_ocr"


class FuenteEjercicio(str, Enum):
    """Origen del ejercicio."""

    MANUAL = "manual"
    GENERADO_IA = "generado_ia"
    EVAU_2023 = "evau_2023"
    BANCO_EJERCICIOS = "banco_ejercicios"


class TipoPrerequisito(str, Enum):
    """Tipos de prerrequisito entre conceptos."""

    HARD = "hard"
    SOFT = "soft"


class RolUsuario(str, Enum):
    """Roles de usuario."""

    STUDENT = "student"
    TEACHER = "teacher"


class ValidadoPor(str, Enum):
    """Validador del error detectado."""

    SYMPY = "sympy"
    LLM_REVIEW = "llm_review"


class RazonRecomendacion(str, Enum):
    """Razones para recomendar un ejercicio."""

    PREREQUISITO_FALTANTE = "prerequisito_faltante"
    REFUERZO = "refuerzo"
    AVANCE = "avance"


def generate_id() -> str:
    """Genera UUID v7-like (timestamp + random)."""
    return str(uuid4())


def now_utc() -> datetime:
    """Timestamp UTC actual."""
    return datetime.utcnow()


@dataclass(frozen=True, slots=True)
class TestRelation:
    """Relación :TESTS entre Ejercicio y Concepto."""

    concepto_codigo: str
    peso: Annotated[float, Field(ge=0.0, le=1.0)]
    es_principal: bool = False


class Concepto(BaseModel):
    """Concepto curricular atómico (Matemáticas II: Cálculo)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(default_factory=generate_id)
    codigo: Annotated[str, Field(min_length=1, pattern=r"^[A-Z]{3}-\d{2}$")]
    nombre: Annotated[str, Field(min_length=1)]
    bloque: BloqueConcepto
    nivel: Annotated[int, Field(ge=1, le=3)]
    descripcion: str
    latex_definicion: LatexString
    prerequisitos_codigos: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)

    @field_validator("codigo")
    @classmethod
    def validate_codigo_format(cls, v: str) -> str:
        if not v.upper().startswith(("LIM", "DER", "INT", "OPT", "CON")):
            raise ValueError("Código debe empezar con prefijo de bloque válido (LIM, DER, INT, OPT, CON)")
        return v.upper()


class Ejercicio(BaseModel):
    """Instancia de problema asignable a la alumna."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(default_factory=generate_id)
    enunciado_latex: LatexString
    enunciado_texto: Annotated[str, Field(min_length=1)]
    tipo: TipoEjercicio
    dificultad: Annotated[int, Field(ge=1, le=5)]
    tiempo_estimado: Annotated[int, Field(ge=1, le=120)]
    fuente: FuenteEjercicio
    metadata_json: str = "{}"
    solucion_canonica_latex: LatexString | None = None
    pasos_solucion: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class Intento(BaseModel):
    """Resolución de la alumna persistida tras OCR."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(default_factory=generate_id)
    ejercicio_id: Annotated[str, Field(min_length=1)]
    alumna_id: Annotated[str, Field(min_length=1)]
    imagenes: list[str] = Field(default_factory=list, max_length=5)
    latex_extraido: LatexString
    pasos_structurados: str  # JSON string: [{"paso": 1, "latex": "...", "descripcion": "..."}]
    estado: EstadoIntento = EstadoIntento.PENDIENTE
    puntuacion: Annotated[float, Field(ge=0.0, le=10.0)] = 0.0
    metadatos_ocr: str = "{}"  # JSON: {"strategy": "...", "confidence": 0.9, "fallback_used": false}
    created_at: datetime = Field(default_factory=now_utc)
    corregido_at: datetime | None = None


class PatronDeError(BaseModel):
    """Error matemático tipificado y recurrente."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(default_factory=generate_id)
    codigo: Annotated[str, Field(min_length=1, pattern=r"^ERR-[A-Z0-9-]+$")]
    nombre: Annotated[str, Field(min_length=1)]
    descripcion: str
    concepto_codigo: Annotated[str, Field(min_length=1)]
    severidad: Annotated[int, Field(ge=1, le=3)]
    frecuencia_global: int = 0
    ejemplo_latex: LatexString
    correccion_latex: LatexString
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class User(BaseModel):
    """Alumna/Profesor (MVP: single-user simplificado)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: Annotated[str, Field(min_length=1)]
    nombre: Annotated[str, Field(min_length=1)]
    email: str | None = None
    rol: RolUsuario = RolUsuario.STUDENT
    created_at: datetime = Field(default_factory=now_utc)


class SesionEstudio(BaseModel):
    """Agregado temporal para analytics de sesión."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(default_factory=generate_id)
    alumna_id: Annotated[str, Field(min_length=1)]
    inicio: datetime
    fin: datetime | None = None
    ejercicios_count: int = 0
    score_promedio: Annotated[float, Field(ge=0.0, le=10.0)] = 0.0
    created_at: datetime = Field(default_factory=now_utc)


class MasteryLevel(BaseModel):
    """Nivel de dominio dinámico (relación :MASTERY_LEVEL)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    alumna_id: Annotated[str, Field(min_length=1)]
    concepto_codigo: Annotated[str, Field(min_length=1)]
    nivel: Annotated[float, Field(ge=0.0, le=1.0)]
    ultima_actualizacion: datetime = Field(default_factory=now_utc)
    intentos_totales: int = 0
    aciertos_consecutivos: int = 0


class HasErrorRelation(BaseModel):
    """Relación :HAS_ERROR entre Intento y PatronDeError."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    intento_id: Annotated[str, Field(min_length=1)]
    patron_codigo: Annotated[str, Field(min_length=1)]
    paso: Annotated[int, Field(ge=1)]
    confianza: Annotated[float, Field(ge=0.0, le=1.0)]
    validado_por: ValidadoPor = ValidadoPor.SYMPY
    detectado_en: datetime = Field(default_factory=now_utc)


class RecommendsRelation(BaseModel):
    """Relación :RECOMMENDS entre Concepto y Ejercicio."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    concepto_codigo: Annotated[str, Field(min_length=1)]
    ejercicio_id: Annotated[str, Field(min_length=1)]
    razon: RazonRecomendacion
    prioridad: Annotated[int, Field(ge=1)]
