"""Capa agnóstica de proveedores LLM (Protocol + Adapters + Factory)."""

from mathtutor.llm.protocol import (
    LLMProtocol,
    ToolCallingLLM,
    LLMRequest,
    LLMResponse,
    LLMError,
)
from mathtutor.llm.factory import LLMFactory

__all__ = [
    "LLMProtocol",
    "ToolCallingLLM",
    "LLMRequest",
    "LLMResponse",
    "LLMError",
    "LLMFactory",
]
