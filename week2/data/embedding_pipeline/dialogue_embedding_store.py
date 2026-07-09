"""生成旧 CSDS 对话级 embedding。

这个脚本是 week1 第一版 `filter/embedding_store.py` 的 week2/data 副本，用于保留
`dialogue_embeddings.h5` 的可复现生成入口。通常不需要重跑；除非旧 CSDS 数据或
embedding 模型明确变化。
"""

from __future__ import annotations

import os
from pathlib import Path

import h5py

from h5_embedding_utils import encode_texts_to_h5, save_json


DATA_ROOT = Path(__file__).resolve().parents[1]
CSDS_DIR = DATA_ROOT / "CSDS"
EMBEDDINGS_DIR = DATA_ROOT / "embeddings"
OUTPUT_FILENAME = "dialogue_embeddings.h5"
METADATA_FILENAME = "dialogue_metadata.json"
EMBED_PREFIX = os.environ.get(
    "EMBED_PREFIX",
    (
        "Instruct: Represent the following Chinese customer service dialogue "
        "for topic filtering, clustering, and semantic analysis.\n"
        "Text: "
    ),
)


def load_datasets() -> dict[str, list[dict]]:
    """读取 CSDS 的 train/val/test 三个 split。"""
    import json

    datasets = {}
    for split in ("train", "val", "test"):
        datasets[split] = json.loads((CSDS_DIR / f"{split}.json").read_text(encoding="utf-8"))
    return datasets


def dialogue_to_text(sample: dict) -> str:
    """把一条多轮对话拼成单个 embedding 文本。"""
    turns = []
    for turn in sample.get("Dialogue", []):
        speaker = turn.get("speaker", "")
        utterance = str(turn.get("utterance", "")).strip()
        if utterance:
            turns.append(f"{speaker}: {utterance}")
    return "\n".join(turns)


def build_texts_and_metadata(dataset: list[dict]) -> tuple[list[str], list[dict]]:
    """整理一个 split 的待编码文本和追溯 metadata。"""
    texts = []
    metadata = []
    for index, sample in enumerate(dataset):
        text = dialogue_to_text(sample)
        if EMBED_PREFIX:
            text = f"{EMBED_PREFIX}{text}"
        texts.append(text)
        metadata.append(
            {
                "index": index,
                "session_id": sample.get("Session_id"),
                "dialogue_id": sample.get("DialogueID"),
                "turn_count": len(sample.get("Dialogue", [])),
            }
        )
    return texts, metadata


def main() -> None:
    """生成或续跑 `dialogue_embeddings.h5`。"""
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    h5_path = EMBEDDINGS_DIR / OUTPUT_FILENAME
    metadata_by_split = {}
    datasets = load_datasets()

    with h5py.File(h5_path, "a") as h5_file:
        for split_name, dataset in datasets.items():
            print(f"开始编码 {split_name}，样本数={len(dataset)}")
            texts, metadata = build_texts_and_metadata(dataset)
            shape = encode_texts_to_h5(split_name=split_name, texts=texts, h5_file=h5_file)
            metadata_by_split[split_name] = metadata
            print(f"{split_name} 编码完成，shape={shape}")

    save_json(metadata_by_split, EMBEDDINGS_DIR / METADATA_FILENAME)
    print(f"已写入: {h5_path}")
    print(f"已写入: {EMBEDDINGS_DIR / METADATA_FILENAME}")


if __name__ == "__main__":
    main()
