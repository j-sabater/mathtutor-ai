"""Excepciones de dominio con códigos y contexto estructurado."""

from __future__ import annotations

from typing import Any


class MathTutorError(Exception):
    """Excepción base con código y contexto estructurado."""

    def __init__(self, code: str, message: str, context: dict[str, Any] | None = None):
        self.code = code
        self.context = context or {}
        super().__init__(message)

    def __str__(self) -> str:
        return f"[{self.code}] {super().__str__()} | Context: {self.context}"


class OCRPipelineError(MathTutorError):
    """Error en pipeline OCR (todas las estrategias fallaron)."""
    pass


class SymPyValidationError(MathTutorError):
    """Error de validación matemática con SymPy."""
    pass


class GraphTransactionError(MathTutorError):
    """Error en transacción Neo4j."""
    pass


class LLMProviderError(MathTutorError):
    """Error de proveedor LLM (API, timeout, rate limit)."""
    pass


class ValidationError(MathTutorError):
    """Error de validación de entrada (Pydantic, reglas de negocio)."""
    pass


class NotFoundError(MathTutorError):
    """Recurso no encontrado en BD."""
    pass


class ConfigurationError(MathTutorError):
    """Error de configuración (falta API key, config inválida)."""
    pass


class DomainRuleError(MathTutorError):
    """Violación de regla de dominio (RV-01 a RV-06)."""
    pass


class WorkflowError(MathTutorError):
    """Error en workflow del agente (LangGraph)."""
    pass
