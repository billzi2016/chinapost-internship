import pytest

from post_ai.config import ProviderSettings
from post_ai.providers import ProviderUnavailableError, build_default_registry


def test_default_registry_contains_expected_providers() -> None:
    registry = build_default_registry(ProviderSettings())

    assert registry.names() == ["fastapi", "ollama", "openrouter", "vllm"]


def test_registry_raises_for_unknown_provider() -> None:
    registry = build_default_registry(ProviderSettings())

    with pytest.raises(ProviderUnavailableError):
        registry.get("transformers")
