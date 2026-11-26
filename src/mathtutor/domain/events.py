"""Eventos de dominio para Event Sourcing / Audit Log."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def generate_event_id() -> str:
    return str(uuid4())


def now_utc() -> datetime:
    return datetime.utcnow()


class DomainEvent(BaseModel):
    """Evento base de dominio."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(default_factory=generate_event_id)
    event_type: str
    timestamp: datetime = Field(default_factory=now_utc)
    trace_id: str
    payload: dict


class IntentoCreado(DomainEvent):
    """Emitido tras ingesta OCR exitosa."""

    event_type: Literal["IntentoCreado"] = "IntentoCreado"
    payload: Annotated[dict, Field(..., description={
        "intento_id": "str",
        "ejercicio_id": "str",
        "alumna_id": "str",
        "estado": "str",
    })]


class IntentoCorregido(DomainEvent):
    """Emitido tras corrección completa (SymPy + LLM)."""

    event_type: Literal["IntentoCorregido"] = "IntentoCorregido"
    payload: Annotated[dict, Field(..., description={
        "intento_id": "str",
        "puntuacion": "float",
        "errores": "list[PatronErrorRef]",
        "duracion_ms": "int",
    })]


class MasteryActualizado(DomainEvent):
    """Emitido tras recálculo EWMA de mastery."""

    event_type: Literal["MasteryActualizado"] = "MasteryActualizado"
    payload: Annotated[dict, Field(..., description={
        "alumna_id": "str",
        "concepto_codigo": "str",
        "nivel_anterior": "float",
        "nivel_nuevo": "float",
        "delta": "float",
    })]


class PatronErrorDetectado(DomainEvent):
    """Emitido al detectar patrón de error (primera vez o recurrencia)."""

    event_type: Literal["PatronErrorDetectado"] = "PatronErrorDetectado"
    payload: Annotated[dict, Field(..., description={
        "intento_id": "str",
        "patron_codigo": "str",
        "paso": "int",
        "confianza": "float",
        "nueva_instancia": "bool",
    })]


class EjercicioRecomendado(DomainEvent):
    """Emitido cuando el agente genera una recomendación."""

    event_type: Literal["EjercicioRecomendado"] = "EjercicioRecomendado"
    payload: Annotated[dict, Field(..., description={
        "alumna_id": "str",
        "ejercicio_id": "str",
        "concepto_objetivo": "str",
        "razon": "str",
        "prioridad": "int",
    })]


class ApunteGenerado(DomainEvent):
    """Emitido al completar generación de apunte personalizado."""

    event_type: Literal["ApunteGenerado"] = "ApunteGenerado"
    payload: Annotated[dict, Field(..., description={
        "alumna_id": "str",
        "conceptos_cubiertos": "list[str]",
        "patrones_abordados": "list[str]",
        "url_pdf": "str",
    })]


# Factory functions para crear eventos con payload tipado
def create_intento_creado(
    trace_id: str,
    intento_id: str,
    ejercicio_id: str,
    alumna_id: str,
    estado: str = "pendiente",
) -> IntentoCreado:
    return IntentoCreado(
        trace_id=trace_id,
        payload={
            "intento_id": intento_id,
            "ejercicio_id": ejercicio_id,
            "alumna_id": alumna_id,
            "estado": estado,
        },
    )


def create_intento_corregido(
    trace_id: str,
    intento_id: str,
    puntuacion: float,
    errores: list[dict],
    duracion_ms: int,
) -> IntentoCorregido:
    return IntentoCorregido(
        trace_id=trace_id,
        payload={
            "intento_id": intento_id,
            "puntuacion": puntuacion,
            "errores": errores,
            "duracion_ms": duracion_ms,
        },
    )


def create_mastery_actualizado(
    trace_id: str,
    alumna_id: str,
    concepto_codigo: str,
    nivel_anterior: float,
    nivel_nuevo: float,
) -> MasteryActualizado:
    return MasteryActualizado(
        trace_id=trace_id,
        payload={
            "alumna_id": alumna_id,
            "concepto_codigo": concepto_codigo,
            "nivel_anterior": nivel_anterior,
            "nivel_nuevo": nivel_nuevo,
            "delta": nivel_nuevo - nivel_anterior,
        },
    )


def create_patron_error_detectado(
    trace_id: str,
    intento_id: str,
    patron_codigo: str,
    paso: int,
    confianza: float,
    nueva_instancia: bool,
) -> PatronErrorDetectado:
    return PatronErrorDetectado(
        trace_id=trace_id,
        payload={
            "intento_id": intento_id,
            "patron_codigo": patron_codigo,
            "paso": paso,
            "confianza": confianza,
            "nueva_instancia": nueva_instancia,
        },
    )


def create_ejercicio_recomendado(
    trace_id: str,
    alumna_id: str,
    ejercicio_id: str,
    concepto_objetivo: str,
    razon: str,
    prioridad: int,
) -> EjercicioRecomendado:
    return EjercicioRecomendado(
        trace_id=trace_id,
        payload={
            "alumna_id": alumna_id,
            "ejercicio_id": ejercicio_id,
            "concepto_objetivo": concepto_objetivo,
            "razon": razon,
            "prioridad": prioridad,
        },
    )


def create_apunte_generado(
    trace_id: str,
    alumna_id: str,
    conceptos_cubiertos: list[str],
    patrones_abordados: list[str],
    url_pdf: str,
) -> ApunteGenerado:
    return ApunteGenerado(
        trace_id=trace_id,
        payload={
            "alumna_id": alumna_id,
            "conceptos_cubiertos": conceptos_cubiertos,
            "patrones_abordados": patrones_abordados,
            "url_pdf": url_pdf,
        },
    )
