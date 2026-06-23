from __future__ import annotations

from post_ai.schemas import RetrievalHit
from post_ai.vectorstores.base import VectorStore, VectorStoreUnavailableError


class PgVectorStore(VectorStore):
    name = "pgvector"

    def __init__(self, dsn: str | None, table: str = "rag_postalembedding") -> None:
        self.dsn = dsn
        self.table = table

    def search(self, query_vector: list[float], top_k: int = 5) -> list[RetrievalHit]:
        raise VectorStoreUnavailableError(
            "pgvector store is a placeholder in the FAISS phase. "
            "Configure PostgreSQL and implement this adapter when Django is integrated."
        )
