"""Protocolos base para capa agnóstica LLM."""

from __future__ import annotations

from typing import Protocol, AsyncIterator, Literal
from pydantic import BaseModel, ConfigDict, Field
from returns.result import Result


class LLMRequest(BaseModel):
    """Request unificado para generación de texto."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    prompt: str
    system_prompt: str | None = None
    temperature: float = 0.0
    max_tokens: int | None = None
    stop_sequences: list[str] = Field(default_factory=list)


class LLMResponse(BaseModel):
    """Response unificado de generación."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    text: str
    usage: dict = Field(default_factory=dict)  # input_tokens, output_tokens, total_tokens
    model: str
    provider: str


class LLMError(BaseModel):
    """Error de proveedor LLM."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    code: str
    message: str
    provider: str
    recoverable: bool


class LLMProtocol(Protocol):
    """Capa base: solo generación de texto (sin tool-calling)."""

    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    async def generate(self, request: LLMRequest) -> Result[LLMResponse, LLMError]: ...

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]: ...


class ToolCallingLLM(LLMProtocol, Protocol):
    """Extensión para proveedores con tool-calling (Claude, GPT-4o, etc.)."""

    class Tool(BaseModel):
        model_config = ConfigDict(extra="forbid", frozen=True)
        name: str
        description: str
        parameters: dict  # JSON Schema

    async def chat_with_tools(
        self,
        messages: list[dict],  # [{"role": "user", "content": "..."}]
        tools: list[Tool],
        tool_choice: Literal["auto", "required", "none"] = "auto",
        response_format: dict | None = None,
    ) -> Result[LLMResponse, LLMError]: ...
