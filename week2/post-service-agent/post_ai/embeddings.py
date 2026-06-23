from __future__ import annotations

from post_ai.providers.base import ModelProvider
from post_ai.schemas import EmbeddingResult


POSTAL_RETRIEVAL_INSTRUCTION = (
    "Given a Chinese postal customer-service query, "
    "retrieve relevant postal-service dialogue passages that answer the query"
)


def build_query_embedding_input(query: str) -> str:
    return f"Instruct: {POSTAL_RETRIEVAL_INSTRUCTION}\nQuery:{query}"


def build_document_embedding_input(text: str) -> str:
    return text


def embed_query(provider: ModelProvider, query: str, model: str) -> EmbeddingResult:
    return provider.embed([build_query_embedding_input(query)], model=model)


def embed_documents(provider: ModelProvider, texts: list[str], model: str) -> EmbeddingResult:
    return provider.embed([build_document_embedding_input(text) for text in texts], model=model)
