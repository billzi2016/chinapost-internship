"""离线 embedding HDF5 写入工具。

这份工具抽自 week1 第一版 filter 流程，用于在 week2/data 下继续维护可复用的
embedding artifact。它不依赖 Django，只依赖 Ollama、h5py 和 numpy。
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import ollama
from tqdm import tqdm


OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "qwen3-embedding:8b")
EMBED_BATCH_SIZE = int(os.environ.get("EMBED_BATCH_SIZE", "8"))
WRITE_BATCH_SIZE = int(os.environ.get("WRITE_BATCH_SIZE", "32"))
SLEEP_SECONDS = float(os.environ.get("EMBED_SLEEP_SECONDS", "0.5"))
OLLAMA_CLIENT = ollama.Client(host=OLLAMA_URL)


def embed_batch(texts: Sequence[str]) -> np.ndarray:
    """用 Ollama embedding 接口编码一个 batch。"""
    try:
        response = OLLAMA_CLIENT.embed(model=EMBED_MODEL, input=list(texts))
    except Exception as exc:
        raise RuntimeError(
            f"请求 Ollama embed 失败: {exc}. 请确认 ollama serve 正在运行，"
            f"并检查模型 {EMBED_MODEL!r} 是否可用。"
        ) from exc

    embeddings = response.get("embeddings")
    if not embeddings:
        raise RuntimeError("ollama.Client.embed(...) 没有返回 embeddings。")
    return np.asarray(embeddings, dtype=np.float32)


def ensure_split_dataset(
    h5_file: h5py.File,
    split_name: str,
    total_count: int,
    embedding_dim: int,
) -> h5py.Dataset:
    """确保 split dataset 存在，并检查 shape 是否和当前数据一致。"""
    if split_name not in h5_file:
        dataset = h5_file.create_dataset(
            split_name,
            shape=(total_count, embedding_dim),
            dtype=np.float32,
            compression="gzip",
            compression_opts=1,
        )
        dataset.attrs["completed"] = 0
        dataset.attrs["embedding_model"] = EMBED_MODEL
        return dataset

    dataset = h5_file[split_name]
    if dataset.shape != (total_count, embedding_dim):
        raise RuntimeError(
            f"{split_name} 数据集 shape 不匹配，现有 {dataset.shape}，"
            f"预期 {(total_count, embedding_dim)}。如果数据源变了，请先备份并删除旧 H5。"
        )
    if "completed" not in dataset.attrs:
        dataset.attrs["completed"] = 0
    return dataset


def flush_embedding_buffer(
    split_dataset: h5py.Dataset,
    start_index: int,
    buffer_arrays: list[np.ndarray],
    h5_file: h5py.File,
) -> int:
    """把暂存在内存里的向量合并后切片写入 HDF5。"""
    if not buffer_arrays:
        return start_index

    merged = np.concatenate(buffer_arrays, axis=0)
    end_index = start_index + merged.shape[0]
    split_dataset[start_index:end_index] = merged
    split_dataset.attrs["completed"] = end_index
    h5_file.flush()
    return end_index


def encode_texts_to_h5(
    *,
    split_name: str,
    texts: Sequence[str],
    h5_file: h5py.File,
) -> tuple[int, int]:
    """把一组文本编码到一个 HDF5 split dataset，支持断点续跑。"""
    total_count = len(texts)
    if total_count == 0:
        if split_name not in h5_file:
            empty_dataset = h5_file.create_dataset(
                split_name,
                shape=(0, 0),
                dtype=np.float32,
                compression="gzip",
                compression_opts=1,
            )
            empty_dataset.attrs["completed"] = 0
        return (0, 0)

    probe_dataset = h5_file.get(split_name)
    if probe_dataset is not None and probe_dataset.attrs.get("completed", 0) > 0:
        completed = int(probe_dataset.attrs["completed"])
        embedding_dim = probe_dataset.shape[1]
        split_dataset = ensure_split_dataset(h5_file, split_name, total_count, embedding_dim)
    else:
        first_end = min(EMBED_BATCH_SIZE, total_count)
        first_embeddings = embed_batch(texts[:first_end])
        embedding_dim = first_embeddings.shape[1]
        split_dataset = ensure_split_dataset(h5_file, split_name, total_count, embedding_dim)
        completed = int(split_dataset.attrs.get("completed", 0))

        if completed == 0:
            split_dataset[0:first_end] = first_embeddings
            split_dataset.attrs["completed"] = first_end
            h5_file.flush()
            completed = first_end
            time.sleep(SLEEP_SECONDS)

    total_batches = (total_count + EMBED_BATCH_SIZE - 1) // EMBED_BATCH_SIZE
    completed_batches = completed // EMBED_BATCH_SIZE

    with tqdm(
        total=total_batches,
        initial=completed_batches,
        desc=f"{split_name} embedding batches",
        unit="batch",
    ) as progress_bar:
        start = completed
        buffer_arrays: list[np.ndarray] = []
        pending_count = 0

        while start < total_count:
            end = min(start + EMBED_BATCH_SIZE, total_count)
            batch_embeddings = embed_batch(texts[start:end])
            if batch_embeddings.shape[0] != end - start:
                raise RuntimeError(
                    f"{split_name} batch 返回条数不匹配: "
                    f"expected={end - start}, got={batch_embeddings.shape[0]}"
                )
            if batch_embeddings.shape[1] != split_dataset.shape[1]:
                raise RuntimeError(
                    f"{split_name} embedding 维度不匹配: "
                    f"expected={split_dataset.shape[1]}, got={batch_embeddings.shape[1]}"
                )

            buffer_arrays.append(batch_embeddings)
            pending_count += batch_embeddings.shape[0]
            if pending_count >= WRITE_BATCH_SIZE:
                completed = flush_embedding_buffer(
                    split_dataset,
                    completed,
                    buffer_arrays,
                    h5_file,
                )
                buffer_arrays = []
                pending_count = 0

            start = end
            progress_bar.update(1)
            time.sleep(SLEEP_SECONDS)

        if buffer_arrays:
            completed = flush_embedding_buffer(split_dataset, completed, buffer_arrays, h5_file)

    return split_dataset.shape


def save_json(data: Any, path: Path) -> None:
    """用统一格式写 JSON metadata。"""
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
