"""Value Objects de dominio (Pydantic v2, frozen=True)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.types import UUID4
import sympy as sp


class LatexString(str):
    """LaTeX string que valida parseabilidad con SymPy."""

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: Any, handler: Any) -> dict:
        return handler(core_schema)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> Any:
        from pydantic_core import core_schema

        return core_schema.with_info_plain_validator_function(
            cls._validate,
            core_schema.str_schema(min_length=1),
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def _validate(cls, value: str, _info: Any) -> str:
        """Valida que el LaTeX sea parseable por SymPy."""
        try:
            sp.parse_latex(value)
        except Exception as e:
            raise ValueError(f"LaTeX no parseable por SymPy: {e}")
        return value


class PasoMatematico(BaseModel):
    """Paso individual en la resolución de un ejercicio."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    numero: Annotated[int, Field(ge=1)]
    latex: LatexString
    descripcion: str = ""
    expresion_sympy: sp.Expr | None = Field(default=None, exclude=True, repr=False)

    @field_validator("latex", mode="before")
    @classmethod
    def _validate_latex(cls, v: str) -> str:
        return LatexString._validate(v, None)


class PatronErrorRef(BaseModel):
    """Referencia a un patrón de error detectado en un paso."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    codigo: Annotated[str, Field(min_length=1, pattern=r"^ERR-[A-Z0-9-]+$")]
    paso: Annotated[int, Field(ge=1)]
    confianza: Annotated[float, Field(ge=0.0, le=1.0)]


class MasterySnapshot(BaseModel):
    """Fotografía del nivel de dominio de un concepto en un momento."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    concepto_codigo: Annotated[str, Field(min_length=1)]
    nivel: Annotated[float, Field(ge=0.0, le=1.0)]
    aciertos_consecutivos: Annotated[int, Field(ge=0)]
    ultima_actualizacion: datetime


class OCRResult(BaseModel):
    """Resultado del pipeline OCR híbrido."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    latex_raw: LatexString
    pasos_structurados: list[PasoMatematico]
    strategy_used: str
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
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


# Type aliases para uso interno
LatexExpr = str  # Serialized sympy expression (srepr)
SymPyExpr = sp.Expr  # Tipo real de SymPy (excluido de serialización)
