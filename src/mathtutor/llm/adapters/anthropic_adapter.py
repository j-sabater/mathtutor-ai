"""Adapter para Anthropic (Claude)."""

from __future__ import annotations

import anthropic
from typing import AsyncIterator
from returns.result import Result, Success, Failure

from mathtutor.llm.protocol import (
    LLMProtocol,
    ToolCallingLLM,
    LLMRequest,
    LLMResponse,
    LLMError,
)


class AnthropicAdapter(ToolCallingLLM):
    """Adapter para Anthropic API."""

    provider_name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY es requerido")
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model_name = model

    async def generate(self, request: LLMRequest) -> Result[LLMResponse, LLMError]:
        try:
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})

            resp = await self.client.messages.create(
                model=self.model_name,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens or 4096,
                stop_sequences=request.stop_sequences or None,
            )

            return Success(LLMResponse(
                text=resp.content[0].text if resp.content else "",
                usage={
                    "input_tokens": resp.usage.input_tokens,
                    "output_tokens": resp.usage.output_tokens,
                },
                model=self.model_name,
                provider=self.provider_name,
            ))
        except anthropic.APIError as e:
            return Failure(LLMError(
                code="ANTHROPIC_API_ERROR",
                message=str(e),
                provider=self.provider_name,
                recoverable=e.status_code in (429, 500, 503),
            ))
        except Exception as e:
            return Failure(LLMError(
                code="ANTHROPIC_UNEXPECTED_ERROR",
                message=str(e),
                provider=self.provider_name,
                recoverable=False,
            ))

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        stream = await self.client.messages.create(
            model=self.model_name,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens or 4096,
            stream=True,
        )

        async for chunk in stream:
            if chunk.type == "content_block_delta":
                yield chunk.delta.text

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[ToolCallingLLM.Tool],
        tool_choice: str = "auto",
        response_format: dict | None = None,
    ) -> Result[LLMResponse, LLMError]:
        try:
            # Convertir tools a formato Anthropic
            anthropic_tools = []
            for tool in tools:
                anthropic_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.parameters,
                })

            resp = await self.client.messages.create(
                model=self.model_name,
                messages=messages,
                tools=anthropic_tools,
                tool_choice=tool_choice,
            )

            return Success(LLMResponse(
                text=resp.content[0].text if resp.content else "",
                usage={
                    "input_tokens": resp.usage.input_tokens,
                    "output_tokens": resp.usage.output_tokens,
                },
                model=self.model_name,
                provider=self.provider_name,
            ))
        except anthropic.APIError as e:
            return Failure(LLMError(
                code="ANTHROPIC_API_ERROR",
                message=str(e),
                provider=self.provider_name,
                recoverable=e.status_code in (429, 500, 503),
            ))
