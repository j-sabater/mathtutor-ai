"""Adapter para OpenAI (GPT-4o)."""

from __future__ import annotations

from openai import AsyncOpenAI
from typing import AsyncIterator
from returns.result import Result, Success, Failure

from mathtutor.llm.protocol import (
    LLMProtocol,
    ToolCallingLLM,
    LLMRequest,
    LLMResponse,
    LLMError,
)


class OpenAIAdapter(ToolCallingLLM):
    """Adapter para OpenAI API."""

    provider_name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-2024-08-06"):
        if not api_key:
            raise ValueError("OPENAI_API_KEY es requerido")
        self.client = AsyncOpenAI(api_key=api_key)
        self.model_name = model

    async def generate(self, request: LLMRequest) -> Result[LLMResponse, LLMError]:
        try:
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})

            resp = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stop=request.stop_sequences or None,
            )

            return Success(LLMResponse(
                text=resp.choices[0].message.content or "",
                usage={
                    "input_tokens": resp.usage.prompt_tokens,
                    "output_tokens": resp.usage.completion_tokens,
                },
                model=self.model_name,
                provider=self.provider_name,
            ))
        except Exception as e:
            # OpenAI errors no tienen status_code estándar, asumir recoverable en rate limit
            error_str = str(e).lower()
            recoverable = "rate limit" in error_str or "timeout" in error_str or "503" in error_str
            return Failure(LLMError(
                code="OPENAI_API_ERROR",
                message=str(e),
                provider=self.provider_name,
                recoverable=recoverable,
            ))

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        stream = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[ToolCallingLLM.Tool],
        tool_choice: str = "auto",
        response_format: dict | None = None,
    ) -> Result[LLMResponse, LLMError]:
        try:
            openai_tools = []
            for tool in tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                })

            resp = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=openai_tools,
                tool_choice=tool_choice,
                response_format=response_format,
            )

            return Success(LLMResponse(
                text=resp.choices[0].message.content or "",
                usage={
                    "input_tokens": resp.usage.prompt_tokens,
                    "output_tokens": resp.usage.completion_tokens,
                },
                model=self.model_name,
                provider=self.provider_name,
            ))
        except Exception as e:
            error_str = str(e).lower()
            recoverable = "rate limit" in error_str or "timeout" in error_str or "503" in error_str
            return Failure(LLMError(
                code="OPENAI_API_ERROR",
                message=str(e),
                provider=self.provider_name,
                recoverable=recoverable,
            ))
