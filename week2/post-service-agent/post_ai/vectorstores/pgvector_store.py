from __future__ import annotations

import re
from typing import Any

from post_ai.schemas import PostalDocument, RetrievalHit
from post_ai.vectorstores.base import VectorStore, VectorStoreUnavailableError


class PgVectorStore(VectorStore):
    name = "pgvector"

    def __init__(self, dsn: str | None, table: str = "core_postalembedding") -> None:
        self.dsn = dsn
        self.table = _validate_table_name(table)

    def search(self, query_vector: list[float], top_k: int = 5) -> list[RetrievalHit]:
        if not self.dsn:
            raise VectorStoreUnavailableError("pgvector DSN is not configured.")

        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise VectorStoreUnavailableError(
                "psycopg is required for pgvector search. Install psycopg[binary]."
            ) from exc

        query_literal = _to_vector_literal(query_vector)
        sql = f"""
            SELECT
                d.split,
                d.source_index,
                d.session_id,
                d.dialogue_id,
                d.source_path,
                d.content,
                d.metadata,
                (e.embedding <=> %s::vector) AS distance
            FROM {self.table} e
            JOIN core_postaldocument d ON d.id = e.document_id
            ORDER BY e.embedding <=> %s::vector
            LIMIT %s
        """
        with psycopg.connect(self.dsn, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, (query_literal, query_literal, top_k))
                rows = cursor.fetchall()

        hits: list[RetrievalHit] = []
        for rank, row in enumerate(rows, start=1):
            document = PostalDocument(
                split=row["split"],
                index=row["source_index"],
                session_id=row["session_id"],
                dialogue_id=row["dialogue_id"],
                source_path=row["source_path"],
                content=row["content"],
                metadata=_metadata_dict(row["metadata"]),
            )
            hits.append(
                RetrievalHit(
                    document=document,
                    score=1.0 - float(row["distance"]),
                    rank=rank,
                )
            )
        return hits


def _to_vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in vector) + "]"


def _metadata_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _validate_table_name(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", value):
        raise VectorStoreUnavailableError(f"Invalid pgvector table name: {value}")
    return value
