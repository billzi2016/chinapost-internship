from __future__ import annotations

from pathlib import Path

from post_ai.config import AppConfig
from post_ai.embeddings import embed_documents, embed_query
from post_ai.filter_mapping import iter_postal_documents, load_filter_results
from post_ai.providers.registry import build_default_registry
from post_ai.retrieval import FaissPostalIndex
from post_ai.schemas import PostalDocument, RetrievalHit
from post_ai.source_loader import load_all_csds


def load_postal_documents(config: AppConfig | None = None) -> list[PostalDocument]:
    config = config or AppConfig.from_env()
    csds_by_split = load_all_csds(config.data_paths.csds_dir)
    filters_by_split = load_filter_results(config.data_paths.filter_path)
    return list(
        iter_postal_documents(
            csds_by_split=csds_by_split,
            filters_by_split=filters_by_split,
            csds_dir=config.data_paths.csds_dir,
        )
    )


def build_faiss_index(
    documents: list[PostalDocument],
    config: AppConfig | None = None,
    batch_size: int = 32,
) -> FaissPostalIndex:
    config = config or AppConfig.from_env()
    settings = config.provider_settings
    registry = build_default_registry(settings)
    provider = registry.get(settings.default_embedding_provider)
    vectors: list[list[float]] = []
    for start in range(0, len(documents), batch_size):
        batch = documents[start : start + batch_size]
        result = embed_documents(
            provider=provider,
            texts=[document.content for document in batch],
            model=settings.default_embedding_model,
        )
        vectors.extend(result.vectors)
    return FaissPostalIndex.build(
        documents=documents,
        vectors=vectors,
        embedding_model=settings.default_embedding_model,
        provider=settings.default_embedding_provider,
    )


def query_faiss_index(
    index: FaissPostalIndex,
    query: str,
    config: AppConfig | None = None,
    top_k: int = 5,
) -> list[RetrievalHit]:
    config = config or AppConfig.from_env()
    settings = config.provider_settings
    registry = build_default_registry(settings)
    provider = registry.get(settings.default_embedding_provider)
    result = embed_query(provider=provider, query=query, model=settings.default_embedding_model)
    return index.search(result.vectors[0], top_k=top_k)


def save_faiss_index(index: FaissPostalIndex, artifact_dir: Path) -> None:
    index.save(artifact_dir)
