from __future__ import annotations

from abc import ABC, abstractmethod

from post_ai.schemas import RetrievalHit


class VectorStoreError(RuntimeError):
    pass


class VectorStoreUnavailableError(VectorStoreError):
    pass


class VectorStore(ABC):
    name: str

    @abstractmethod
    def search(self, query_vector: list[float], top_k: int = 5) -> list[RetrievalHit]:
        raise NotImplementedError
