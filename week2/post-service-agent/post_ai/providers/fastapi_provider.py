from __future__ import annotations

from post_ai.providers.openai_compatible import OpenAICompatibleProvider


class FastAPIProvider(OpenAICompatibleProvider):
    """Provider for a user-owned model service.

    The service should expose OpenAI-compatible endpoints. This is the supported
    route for SFT models that are served outside the Django process.
    """

    def __init__(self, base_url: str | None = None) -> None:
        super().__init__(name="fastapi", base_url=base_url)
