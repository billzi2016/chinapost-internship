from __future__ import annotations

from post_ai.providers.openai_compatible import OpenAICompatibleProvider


class VLLMProvider(OpenAICompatibleProvider):
    def __init__(self, base_url: str | None = None) -> None:
        super().__init__(name="vllm", base_url=base_url)
