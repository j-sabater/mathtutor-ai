"""Esquemas para revisión OCR (Human-in-the-loop)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from typing import Annotated, Literal


class OCRReviewRequest(BaseModel):
    """Request para aprobar o corregir LaTeX extraído."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action: Literal["approve", "correct"]
    corrected_latex: str | None = None  # Requerido si action="correct"


class OCRReviewResponse(BaseModel):
    """Response de revisión OCR."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["accepted", "rejected", "correction_invalid"]
    trace_id: str
    mensaje: str
