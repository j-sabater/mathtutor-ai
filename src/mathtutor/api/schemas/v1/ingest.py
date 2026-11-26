"""Esquemas para ingesta de intentos."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from typing import Annotated, Literal


class IngestRequest(BaseModel):
    """Request para subir imágenes/PDF de un intento."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ejercicio_id: Annotated[str, Field(min_length=1)]
    alumna_id: str = "alumna_principal"
    imagenes: Annotated[list[HttpUrl], Field(min_length=1, max_length=5)]


class IngestResponse(BaseModel):
    """Response tras ingesta OCR."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trace_id: str
    intento_id: str
    estado: Literal["pendiente_revision", "error_ocr"]
    latex_extraido: str
    pasos_detectados: int
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    strategy_used: str
    fallback_used: bool
    requiere_revision: bool  # True si confidence < 0.7
