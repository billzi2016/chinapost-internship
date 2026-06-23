from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any

from post_ai.schemas import ChatDelta, ChatMessage, ChatResult, EmbeddingResult


class ProviderError(RuntimeError):
    """Base provider error."""


class ProviderUnavailableError(ProviderError):
    """Raised when a configured provider or model is not available."""


class ModelProvider(ABC):
    name: str

    @abstractmethod
    def chat(
        self,
        messages: list[ChatMessage],
        model: str,
        options: dict[str, Any] | None = None,
    ) -> ChatResult:
        raise NotImplementedError

    @abstractmethod
    def stream_chat(
        self,
        messages: list[ChatMessage],
        model: str,
        options: dict[str, Any] | None = None,
    ) -> Iterator[ChatDelta]:
        raise NotImplementedError

    @abstractmethod
    def embed(
        self,
        texts: list[str],
        model: str,
        options: dict[str, Any] | None = None,
    ) -> EmbeddingResult:
        raise NotImplementedError

    @abstractmethod
    def is_available(self, model: str) -> bool:
        raise NotImplementedError
