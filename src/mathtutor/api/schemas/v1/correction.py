"""Esquemas para resultado de corrección."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from typing import Annotated, Literal

from mathtutor.domain.value_objects import PatronErrorRef, MasterySnapshot


class StepFeedback(BaseModel):
    """Feedback de un paso individual."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    paso: int
    latex_original: str
    latex_normalizado: str
    es_correcto: bool
    feedback: str
    sugerencia: str | None
    patron_error_codigo: str | None


class CorrectionResult(BaseModel):
    """Resultado completo de corrección."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trace_id: str
    intento_id: str
    puntuacion: Annotated[float, Field(ge=0.0, le=10.0)]
    pasos_feedback: list[StepFeedback]
    errores_detectados: list[PatronErrorRef]
    mastery_actualizado: list[MasterySnapshot]
    ejercicio_recomendado_id: str | None
    apunte_generado_url: str | None
    duracion_ms: int
