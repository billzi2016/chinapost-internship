from __future__ import annotations

import json
from pathlib import Path

import h5py
import numpy as np

from post_ai.schemas import EmbeddingMetadata, SplitName
from post_ai.source_loader import SPLITS


class OldEmbeddingAlignmentError(ValueError):
    pass


def load_embedding_metadata(path: Path) -> dict[SplitName, list[EmbeddingMetadata]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        split: [EmbeddingMetadata.model_validate(item) for item in raw[split]]
        for split in SPLITS
    }


def load_postal_vectors_from_h5(
    h5_path: Path,
    metadata_by_split: dict[SplitName, list[EmbeddingMetadata]],
    selected_keys: list[tuple[SplitName, int, str, int]],
) -> np.ndarray:
    vectors: list[np.ndarray] = []
    with h5py.File(h5_path, "r") as handle:
        for split, index, session_id, dialogue_id in selected_keys:
            metadata = metadata_by_split[split][index]
            if metadata.index != index:
                raise OldEmbeddingAlignmentError(f"{split}[{index}] metadata index mismatch.")
            if metadata.session_id != session_id:
                raise OldEmbeddingAlignmentError(f"{split}[{index}] session_id mismatch.")
            if metadata.dialogue_id != dialogue_id:
                raise OldEmbeddingAlignmentError(f"{split}[{index}] dialogue_id mismatch.")
            vectors.append(handle[split][index])
    if not vectors:
        return np.empty((0, 0), dtype="float32")
    return np.asarray(vectors, dtype="float32")
