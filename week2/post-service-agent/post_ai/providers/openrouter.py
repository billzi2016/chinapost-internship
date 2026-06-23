from __future__ import annotations

from post_ai.providers.openai_compatible import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        super().__init__(name="openrouter", base_url=base_url, api_key=api_key)
