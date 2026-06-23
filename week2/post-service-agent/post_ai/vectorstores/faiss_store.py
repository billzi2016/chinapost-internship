from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np

from post_ai.schemas import PostalDocument, RetrievalHit
from post_ai.vectorstores.base import VectorStore


FAISS_INDEX_FILENAME = "postal.faiss"
FAISS_METADATA_FILENAME = "postal_metadata.json"


class FaissPostalIndex(VectorStore):
    """FAISS vector store adapter.

    Keep FAISS behind this file. When the project switches to pgvector, Django
    should replace this adapter with a pgvector store without changing RAG
    callers.
    """

    name = "faiss"

    def __init__(
        self,
        index: faiss.Index,
        documents: list[PostalDocument],
        embedding_model: str,
        provider: str,
    ) -> None:
        self.index = index
        self.documents = documents
        self.embedding_model = embedding_model
        self.provider = provider

    @classmethod
    def build(
        cls,
        documents: list[PostalDocument],
        vectors: list[list[float]] | np.ndarray,
        embedding_model: str,
        provider: str,
    ) -> "FaissPostalIndex":
        matrix = as_normalized_matrix(vectors)
        if len(documents) != matrix.shape[0]:
            raise ValueError(f"Document/vector mismatch: {len(documents)} != {matrix.shape[0]}.")
        index = faiss.IndexFlatIP(matrix.shape[1])
        index.add(matrix)
        return cls(index=index, documents=documents, embedding_model=embedding_model, provider=provider)

    def search(self, query_vector: list[float] | np.ndarray, top_k: int = 5) -> list[RetrievalHit]:
        if not self.documents:
            return []
        query = as_normalized_matrix([query_vector])
        scores, indices = self.index.search(query, min(top_k, len(self.documents)))
        hits: list[RetrievalHit] = []
        for rank, (score, doc_index) in enumerate(zip(scores[0], indices[0], strict=True), start=1):
            if doc_index < 0:
                continue
            hits.append(
                RetrievalHit(
                    document=self.documents[int(doc_index)],
                    score=float(score),
                    rank=rank,
                )
            )
        return hits

    def save(self, artifact_dir: Path) -> None:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(artifact_dir / FAISS_INDEX_FILENAME))
        payload = {
            "embedding_model": self.embedding_model,
            "provider": self.provider,
            "document_count": len(self.documents),
            "documents": [document.model_dump() for document in self.documents],
        }
        (artifact_dir / FAISS_METADATA_FILENAME).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, artifact_dir: Path) -> "FaissPostalIndex":
        index = faiss.read_index(str(artifact_dir / FAISS_INDEX_FILENAME))
        payload = json.loads((artifact_dir / FAISS_METADATA_FILENAME).read_text(encoding="utf-8"))
        documents = [PostalDocument.model_validate(item) for item in payload["documents"]]
        return cls(
            index=index,
            documents=documents,
            embedding_model=payload["embedding_model"],
            provider=payload["provider"],
        )


def as_normalized_matrix(vectors: list[list[float]] | list[np.ndarray] | np.ndarray) -> np.ndarray:
    matrix = np.asarray(vectors, dtype="float32")
    if matrix.ndim != 2:
        raise ValueError("Vectors must be a 2D matrix.")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms
