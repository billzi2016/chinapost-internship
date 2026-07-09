"""读取离线生成的 policy/FAQ embedding。

policy/FAQ 数据来自 `week2/data/dataset.jsonl`，向量由
`week2/data/embedding_pipeline/policy_embedding_store.py` 离线生成。
这里不调用 embedding provider，只做 H5 和 metadata 的对齐读取。
"""

from __future__ import annotations

import json
from pathlib import Path

import h5py
import numpy as np

from post_ai.schemas import EmbeddingMetadata


POLICY_SPLIT = "policy"


class PolicyEmbeddingMissingError(FileNotFoundError):
    """policy embedding 文件不存在时抛出，提示先跑离线生成脚本。"""


def load_policy_embedding_metadata(path: Path) -> list[EmbeddingMetadata]:
    """读取 policy metadata，并兼容 `{policy: [...]}` 结构。"""
    if not path.exists():
        raise PolicyEmbeddingMissingError(
            f"Policy metadata not found: {path}. "
            "Run `cd week2/data/embedding_pipeline && python policy_embedding_store.py` first."
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    records = raw.get(POLICY_SPLIT, raw) if isinstance(raw, dict) else raw
    return [EmbeddingMetadata.model_validate(item) for item in records]


def load_policy_vectors_from_h5(
    h5_path: Path,
    metadata: list[EmbeddingMetadata],
    selected_keys: list[tuple[int, str, int]],
) -> np.ndarray:
    """按 `(index, session_id, dialogue_id)` 读取 policy 向量并校验对齐。"""
    if not h5_path.exists():
        raise PolicyEmbeddingMissingError(
            f"Policy embedding H5 not found: {h5_path}. "
            "Run `cd week2/data/embedding_pipeline && python policy_embedding_store.py` first."
        )

    vectors: list[np.ndarray] = []
    with h5py.File(h5_path, "r") as handle:
        if POLICY_SPLIT not in handle:
            raise ValueError(f"Policy H5 missing dataset: {POLICY_SPLIT}")
        dataset = handle[POLICY_SPLIT]
        for index, session_id, dialogue_id in selected_keys:
            item = metadata[index]
            if item.index != index:
                raise ValueError(f"policy[{index}] metadata index mismatch.")
            if item.session_id != session_id:
                raise ValueError(f"policy[{index}] session_id mismatch.")
            if item.dialogue_id != dialogue_id:
                raise ValueError(f"policy[{index}] dialogue_id mismatch.")
            vectors.append(dataset[index])
    if not vectors:
        return np.empty((0, 0), dtype="float32")
    return np.asarray(vectors, dtype="float32")
