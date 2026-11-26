"""Core: configuración, logging, excepciones base."""

from mathtutor.core.config import settings, Settings
from mathtutor.core.logging import get_logger, setup_logging
from mathtutor.core.exceptions import (
    MathTutorError,
    OCRPipelineError,
    SymPyValidationError,
    GraphTransactionError,
    LLMProviderError,
    ValidationError,
    NotFoundError,
    ConfigurationError,
)

__all__ = [
    "settings",
    "Settings",
    "get_logger",
    "setup_logging",
    "MathTutorError",
    "OCRPipelineError",
    "SymPyValidationError",
    "GraphTransactionError",
    "LLMProviderError",
    "ValidationError",
    "NotFoundError",
    "ConfigurationError",
]
