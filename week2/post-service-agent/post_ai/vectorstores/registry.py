from __future__ import annotations

from post_ai.config import VectorStoreSettings
from post_ai.vectorstores.base import VectorStore, VectorStoreUnavailableError
from post_ai.vectorstores.faiss_store import FaissPostalIndex
from post_ai.vectorstores.pgvector_store import PgVectorStore


class VectorStoreRegistry:
    def __init__(self) -> None:
        self._stores: dict[str, VectorStore] = {}

    def register(self, store: VectorStore) -> None:
        self._stores[store.name] = store

    def get(self, name: str) -> VectorStore:
        try:
            return self._stores[name]
        except KeyError as exc:
            available = ", ".join(sorted(self._stores)) or "none"
            raise VectorStoreUnavailableError(
                f"Vector store '{name}' is not registered. Available stores: {available}."
            ) from exc


def build_vector_store_registry(settings: VectorStoreSettings) -> VectorStoreRegistry:
    registry = VectorStoreRegistry()
    if settings.faiss_artifact_dir:
        registry.register(FaissPostalIndex.load(settings.faiss_artifact_dir))
    registry.register(PgVectorStore(dsn=settings.pgvector_dsn, table=settings.pgvector_table))
    return registry
