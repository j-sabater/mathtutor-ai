"""Estado global del agente (LangGraph StateGraph)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from langgraph.graph import add_messages

from mathtutor.domain.value_objects import (
    PasoMatematico,
    PatronErrorRef,
    MasterySnapshot,
)


class OCRResult(BaseModel):
    """Resultado del pipeline OCR híbrido."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    latex_raw: str
    pasos_structurados: list[PasoMatematico]
    strategy_used: str
    confidence: float
    fallback_used: bool
    imagenes_paths: list[str] = Field(default_factory=list)


class StepValidation(BaseModel):
    """Resultado de validación de un paso matemático."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    paso_numero: Annotated[int, Field(ge=1)]
    latex_original: str
    latex_normalizado: str
    expresion_sympy: str  # repr serializado de sp.Expr
    es_correcto: bool
    tipo_error: str | None = None
    mensaje_feedback: str
    sugerencia_correccion: str | None = None


class ErrorClassification(BaseModel):
    """Clasificación de error detectado."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    patron_codigo: Annotated[str, Field(min_length=1, pattern=r"^ERR-[A-Z0-9-]+$")]
    paso: Annotated[int, Field(ge=1)]
    confianza: Annotated[float, Field(ge=0.0, le=1.0)]
    es_nueva_instancia: bool


class GraphUpdateResult(BaseModel):
    """Resultado de actualización del grafo de conocimiento."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mastery_actualizado: dict[str, float]  # concepto_codigo -> nuevo_nivel
    errores_persistidos: list[ErrorClassification]
    recomendaciones_creadas: list[str]  # ejercicio_ids


class StreamChunk(BaseModel):
    """Chunk de streaming para WebSocket/HTMX."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["progress", "partial_result", "tool_call", "node_start", "node_end", "error"]
    node: str
    message: str
    data: dict | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trace_id: str


class AgentState(BaseModel):
    """Estado global del workflow de corrección (LangGraph)."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    # Identidad y tracking
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    request_id: str
    alumna_id: str = "alumna_principal"

    # Input
    ejercicio_id: str
    imagenes: list[bytes]  # Subidas multipart

    # Pipeline OCR
    ocr_result: Optional[OCRResult] = None
    ocr_approved: bool = False
    ocr_corrected_latex: Optional[str] = None

    # Corrección
    validaciones: list[StepValidation] = Field(default_factory=list)
    puntuacion_global: Optional[float] = None

    # Clasificación errores
    errores_clasificados: list[ErrorClassification] = Field(default_factory=list)

    # Actualización grafo
    graph_update: Optional[GraphUpdateResult] = None

    # Generación
    ejercicio_recomendado_id: Optional[str] = None
    apunte_generado_url: Optional[str] = None

    # Control de flujo
    current_node: str = "ingest"
    retry_count: int = 0
    max_retries: int = 3
    error: Optional[str] = None

    # Streaming (interno, no serializado)
    stream_queue: Annotated[list[StreamChunk], "internal"] = Field(
        default_factory=list, exclude=True, repr=False
    )
