"""Factory para crear proveedores LLM según configuración."""

from __future__ import annotations

from returns.result import Result, Success, Failure

from mathtutor.llm.protocol import LLMProtocol, LLMError
from mathtutor.core.config import settings


class LLMFactory:
    """Factory que crea instancias de proveedores LLM."""

    @staticmethod
    def create(provider: str | None = None, **kwargs) -> Result[LLMProtocol, LLMError]:
        provider = provider or settings.llm_provider

        if provider == "anthropic":
            return Success(_create_anthropic(**kwargs))
        elif provider == "openai":
            return Success(_create_openai(**kwargs))
        elif provider == "ollama":
            return Success(_create_ollama(**kwargs))
        else:
            return Failure(LLMError(
                code="UNKNOWN_PROVIDER",
                message=f"Proveedor no soportado: {provider}",
                provider="factory",
                recoverable=False
            ))


def _create_anthropic(**kwargs) -> LLMProtocol:
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic package not installed. Install with: pip install mathtutor-ai[anthropic]")

    from mathtutor.llm.adapters.anthropic_adapter import AnthropicAdapter

    return AnthropicAdapter(
        api_key=kwargs.get("api_key", settings.anthropic_api_key),
        model=kwargs.get("model", settings.anthropic_model),
    )


def _create_openai(**kwargs) -> LLMProtocol:
    try:
        import openai
    except ImportError:
        raise RuntimeError("openai package not installed. Install with: pip install mathtutor-ai[openai]")

    from mathtutor.llm.adapters.openai_adapter import OpenAIAdapter

    return OpenAIAdapter(
        api_key=kwargs.get("api_key", settings.openai_api_key),
        model=kwargs.get("model", settings.openai_model),
    )


def _create_ollama(**kwargs) -> LLMProtocol:
    try:
        import ollama
    except ImportError:
        raise RuntimeError("ollama package not installed. Install with: pip install mathtutor-ai[ollama]")

    from mathtutor.llm.adapters.ollama_adapter import OllamaAdapter

    return OllamaAdapter(
        base_url=kwargs.get("base_url", settings.ollama_base_url),
        model=kwargs.get("model", settings.ollama_model),
    )
