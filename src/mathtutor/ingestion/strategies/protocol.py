"""Protocol e interfaces para estrategias OCR (Strategy Pattern)."""

from __future__ import annotations

from typing import Protocol
from pydantic import BaseModel, ConfigDict, Field
from returns.result import Result


class OCRRequest(BaseModel):
    """Request para procesamiento OCR."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    images: list[bytes]  # Bytes de imagen/PDF
    context: dict = Field(default_factory=dict)  # tipo_ejercicio, conceptos_esperados, etc.


class OCRResponse(BaseModel):
    """Response exitoso de OCR."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    latex_raw: str
    confidence: float
    strategy_name: str
    metadata: dict = Field(default_factory=dict)


class OCRError(BaseModel):
    """Error de estrategia OCR."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    code: str
    message: str
    strategy: str
    recoverable: bool


class OCRStrategy(Protocol):
    """Estrategia de OCR (Local o API). Strategy Pattern."""

    @property
    def name(self) -> str: ...

    @property
    def requires_gpu(self) -> bool: ...

    async def process(self, request: OCRRequest) -> Result[OCRResponse, OCRError]: ...
