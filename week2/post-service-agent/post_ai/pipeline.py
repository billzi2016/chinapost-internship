from __future__ import annotations

from pathlib import Path

from post_ai.config import AppConfig
from post_ai.embeddings import embed_documents, embed_query
from post_ai.filter_mapping import iter_postal_documents, load_filter_results
from post_ai.old_embeddings import load_embedding_metadata, load_postal_vectors_from_h5
from post_ai.policy_embeddings import load_policy_embedding_metadata, load_policy_vectors_from_h5
from post_ai.providers.registry import build_default_registry
from post_ai.schemas import PostalDocument, RetrievalHit
from post_ai.source_loader import load_all_csds, load_policy_jsonl
from post_ai.vectorstores import FaissPostalIndex, build_vector_store_registry


def load_postal_documents(config: AppConfig | None = None) -> list[PostalDocument]:
    config = config or AppConfig.from_env()
    return load_csds_postal_documents(config) + load_policy_documents(config)


def load_csds_postal_documents(config: AppConfig | None = None) -> list[PostalDocument]:
    """加载旧 CSDS + LLM filter 产生的邮政对话文档。"""
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


def load_policy_documents(config: AppConfig | None = None) -> list[PostalDocument]:
    """加载 week1 爬虫产出的政策/FAQ JSONL 文档。"""
    config = config or AppConfig.from_env()
    return load_policy_jsonl(config.data_paths.policy_dataset_jsonl_path)


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


def query_configured_vector_store(
    query: str,
    config: AppConfig | None = None,
    top_k: int = 5,
) -> list[RetrievalHit]:
    config = config or AppConfig.from_env()
    settings = config.provider_settings
    registry = build_default_registry(settings)
    embedding_provider = registry.get(settings.default_embedding_provider)
    embedding = embed_query(
        provider=embedding_provider,
        query=query,
        model=settings.default_embedding_model,
    )
    vector_stores = build_vector_store_registry(config.vector_store_settings)
    store = vector_stores.get(config.vector_store_settings.provider)
    return store.search(embedding.vectors[0], top_k=top_k)


def save_faiss_index(index: FaissPostalIndex, artifact_dir: Path) -> None:
    index.save(artifact_dir)


def build_faiss_index_from_old_h5(config: AppConfig | None = None) -> FaissPostalIndex:
    config = config or AppConfig.from_env()
    legacy_documents = load_csds_postal_documents(config)
    policy_documents = load_policy_documents(config)
    metadata_by_split = load_embedding_metadata(config.data_paths.embedding_metadata_path)
    selected_keys = [
        (document.split, document.index, document.session_id, document.dialogue_id)
        for document in legacy_documents
    ]
    legacy_vectors = load_postal_vectors_from_h5(
        h5_path=config.data_paths.old_embedding_h5_path,
        metadata_by_split=metadata_by_split,
        selected_keys=selected_keys,
    )
    documents = legacy_documents + policy_documents
    vectors = legacy_vectors.tolist()
    embedding_model = "dialogue_embeddings.h5"
    provider = "old-h5"
    if policy_documents:
        policy_metadata = load_policy_embedding_metadata(config.data_paths.policy_embedding_metadata_path)
        policy_vectors = load_policy_vectors_from_h5(
            h5_path=config.data_paths.policy_embedding_h5_path,
            metadata=policy_metadata,
            selected_keys=[
                (document.index, document.session_id, document.dialogue_id)
                for document in policy_documents
            ],
        )
        vectors.extend(policy_vectors.tolist())
        embedding_model = f"{embedding_model}+policy_embeddings.h5"
        provider = f"{provider}+policy-h5"
    return FaissPostalIndex.build(
        documents=documents,
        vectors=vectors,
        embedding_model=embedding_model,
        provider=provider,
    )


def build_and_save_faiss_from_old_h5(
    artifact_dir: Path | None = None,
    config: AppConfig | None = None,
) -> FaissPostalIndex:
    config = config or AppConfig.from_env()
    index = build_faiss_index_from_old_h5(config)
    default_artifact_dir = config.vector_store_settings.faiss_artifact_dir or (config.artifact_dir / "faiss")
    index.save(artifact_dir or default_artifact_dir)
    return index
