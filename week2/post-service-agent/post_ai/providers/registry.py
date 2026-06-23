from __future__ import annotations

from post_ai.config import ProviderSettings
from post_ai.providers.base import ModelProvider, ProviderUnavailableError
from post_ai.providers.fastapi_provider import FastAPIProvider
from post_ai.providers.ollama import OllamaProvider
from post_ai.providers.openrouter import OpenRouterProvider
from post_ai.providers.vllm import VLLMProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ModelProvider] = {}

    def register(self, provider: ModelProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> ModelProvider:
        try:
            return self._providers[name]
        except KeyError as exc:
            available = ", ".join(sorted(self._providers)) or "none"
            raise ProviderUnavailableError(
                f"Provider '{name}' is not registered. Available providers: {available}."
            ) from exc

    def names(self) -> list[str]:
        return sorted(self._providers)


def build_default_registry(settings: ProviderSettings) -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(OllamaProvider(base_url=settings.ollama_base_url))
    registry.register(VLLMProvider(base_url=settings.vllm_base_url))
    registry.register(
        OpenRouterProvider(
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key,
        )
    )
    registry.register(FastAPIProvider(base_url=settings.fastapi_base_url))
    return registry
