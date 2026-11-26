"""Esquemas para consulta de progreso (Dashboard)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from typing import Annotated, Literal


class ConceptoProgress(BaseModel):
    """Progreso de un concepto individual."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    codigo: str
    nombre: str
    bloque: str
    mastery: Annotated[float, Field(ge=0.0, le=1.0)]
    nivel: Literal["básico", "intermedio", "avanzado"]
    aciertos_consecutivos: int
    intentos_totales: int
    prerequisitos_faltantes: list[str]


class PatronErrorFrequency(BaseModel):
    """Frecuencia de un patrón de error."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    codigo: str
    nombre: str
    severidad: int
    frecuencia_30d: int
    ultima_ocurrencia: str  # ISO datetime


class ProgressResponse(BaseModel):
    """Response completo de progreso."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    alumna_id: str
    conceptos: list[ConceptoProgress]
    patrones_error_top: list[PatronErrorFrequency]
    racha_actual: int
    siguiente_recomendacion: dict | None  # {ejercicio_id, concepto, razon}
