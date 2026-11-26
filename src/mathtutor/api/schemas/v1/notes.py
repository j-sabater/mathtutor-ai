"""Esquemas para generación de apuntes personalizados."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from typing import Annotated


class GenerateNoteRequest(BaseModel):
    """Request para generar apunte personalizado."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    alumna_id: str = "alumna_principal"
    conceptos_codigos: Annotated[list[str], Field(min_length=1)]
    patrones_objetivo: list[str] = Field(default_factory=list)  # Códigos PatronDeError a abordar


class NoteResponse(BaseModel):
    """Response de generación de apunte."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    note_id: str
    url_pdf: str
    conceptos_cubiertos: list[str]
    patrones_abordados: list[str]
    generated_at: str
