import pytest

from post_ai.config import VectorStoreSettings
from post_ai.vectorstores import VectorStoreUnavailableError, build_vector_store_registry


def test_vectorstore_registry_contains_pgvector_placeholder_without_faiss() -> None:
    registry = build_vector_store_registry(
        VectorStoreSettings(provider="pgvector", faiss_artifact_dir=None)
    )

    store = registry.get("pgvector")
    assert store.name == "pgvector"


def test_vectorstore_registry_raises_for_unknown_store() -> None:
    registry = build_vector_store_registry(
        VectorStoreSettings(provider="pgvector", faiss_artifact_dir=None)
    )

    with pytest.raises(VectorStoreUnavailableError):
        registry.get("unknown")
