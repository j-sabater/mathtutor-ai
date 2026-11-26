"""Adapter para Ollama (local LLM)."""

from __future__ import annotations

import httpx
from typing import AsyncIterator
from returns.result import Result, Success, Failure

from mathtutor.llm.protocol import (
    LLMProtocol,
    LLMRequest,
    LLMResponse,
    LLMError,
)


class OllamaAdapter(LLMProtocol):
    """Adapter para Ollama API local."""

    provider_name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1:70b"):
        self.base_url = base_url.rstrip("/")
        self.model_name = model
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=120.0)

    async def generate(self, request: LLMRequest) -> Result[LLMResponse, LLMError]:
        try:
            prompt = request.prompt
            if request.system_prompt:
                prompt = f"{request.system_prompt}\n\n{prompt}"

            resp = await self.client.post(
                "/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "temperature": request.temperature,
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            return Success(LLMResponse(
                text=data.get("response", ""),
                usage={},  # Ollama no devuelve usage por defecto
                model=self.model_name,
                provider=self.provider_name,
            ))
        except httpx.HTTPStatusError as e:
            return Failure(LLMError(
                code="OLLAMA_HTTP_ERROR",
                message=f"HTTP {e.response.status_code}: {e.response.text}",
                provider=self.provider_name,
                recoverable=e.response.status_code in (429, 500, 503),
            ))
        except Exception as e:
            return Failure(LLMError(
                code="OLLAMA_ERROR",
                message=str(e),
                provider=self.provider_name,
                recoverable=False,
            ))

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        prompt = request.prompt
        if request.system_prompt:
            prompt = f"{request.system_prompt}\n\n{prompt}"

        async with self.client.stream(
            "POST",
            "/api/generate",
            json={
                "model": self.model_name,
                "prompt": prompt,
                "temperature": request.temperature,
                "stream": True,
            },
            timeout=120.0,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line:
                    import json
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]
                    if data.get("done", False):
                        break
