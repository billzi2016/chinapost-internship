from __future__ import annotations

from typing import Any

from post_ai.schemas import PostalDocument, RetrievalHit
from post_ai.vectorstores.base import VectorStore, VectorStoreUnavailableError


class PgVectorStore(VectorStore):
    name = "pgvector"

    def __init__(self, dsn: str | None, table: str = "core_postalembedding") -> None:
        self.dsn = dsn
        self.table = table

    def search(self, query_vector: list[float], top_k: int = 5) -> list[RetrievalHit]:
        from django.db import connection
        from pgvector.django import CosineDistance

        from apps.core.models import PostalEmbedding

        if connection.vendor != "postgresql":
            raise VectorStoreUnavailableError("pgvector search requires Django PostgreSQL connection.")

        rows = (
            PostalEmbedding.objects.select_related("document")
            .annotate(distance=CosineDistance("embedding", query_vector))
            .order_by("distance")[:top_k]
        )

        hits: list[RetrievalHit] = []
        for rank, row in enumerate(rows, start=1):
            source = row.document
            document = PostalDocument(
                split=source.split,
                index=source.source_index,
                session_id=source.session_id,
                dialogue_id=source.dialogue_id,
                source_path=source.source_path,
                content=source.content,
                metadata=_metadata_dict(source.metadata),
            )
            hits.append(
                RetrievalHit(
                    document=document,
                    score=1.0 - float(row.distance),
                    rank=rank,
                )
            )
        return hits


def _metadata_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}
