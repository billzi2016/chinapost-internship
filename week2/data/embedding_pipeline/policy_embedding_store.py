"""生成 week1 爬虫政策/FAQ 数据的独立 embedding H5。

输入是 `week2/data/dataset.jsonl`，输出是：
- `week2/data/embeddings/policy_embeddings.h5`
- `week2/data/embeddings/policy_metadata.json`

这个脚本不写 Django 数据库。Django ingest 只读取这里已经生成好的 H5。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import h5py

from h5_embedding_utils import encode_texts_to_h5, save_json


DATA_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = DATA_ROOT / "dataset.jsonl"
EMBEDDINGS_DIR = DATA_ROOT / "embeddings"
OUTPUT_FILENAME = "policy_embeddings.h5"
METADATA_FILENAME = "policy_metadata.json"
SPLIT_NAME = "policy"
POLICY_PREFIX = (
    "Instruct: Represent the following Chinese postal policy or EMS FAQ "
    "for retrieval in customer service question answering.\n"
    "Text: "
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """读取 policy/FAQ JSONL。"""
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"JSONL line must be object: {path}:{line_number}")
        rows.append(row)
    return rows


def build_policy_text(row: dict[str, Any]) -> str:
    """把一条政策/FAQ 记录整理成稳定的 embedding 文本。"""
    categories = _as_text_list(row.get("policy_categories"))
    requirements = _as_text_list(row.get("requirements"))
    exclusions = _as_text_list(row.get("insurance_exclusions"))
    parts = [
        f"资料来源: {row.get('company') or '中国邮政/EMS'}",
        f"标题: {_as_text(row.get('title'))}",
        f"政策分类: {'、'.join(categories)}",
        f"摘要: {_as_text(row.get('summary'))}",
        f"证据原文: {_as_text(row.get('evidence_text'))}",
    ]
    if requirements:
        parts.append(f"办理要求: {'、'.join(requirements)}")
    if row.get("compensation_limit"):
        parts.append(f"赔付上限: {row['compensation_limit']}")
    if row.get("claim_deadline"):
        parts.append(f"理赔时限: {row['claim_deadline']}")
    if exclusions:
        parts.append(f"保价除外责任: {'、'.join(exclusions)}")
    if row.get("url"):
        parts.append(f"来源链接: {_as_text(row.get('url'))}")
    return f"{POLICY_PREFIX}{chr(10).join(part for part in parts if part.strip())}"


def build_policy_metadata(row: dict[str, Any], index: int) -> dict[str, Any]:
    """保存 policy 文档和向量之间的追溯信息。"""
    categories = _as_text_list(row.get("policy_categories"))
    source_id = _as_text(row.get("source_id")) or "policy_dataset"
    return {
        "index": index,
        "source_kind": "policy_jsonl",
        "source_id": source_id,
        "session_id": f"{source_id}:{index}",
        "dialogue_id": index,
        "turn_count": 1,
        "title": _as_text(row.get("title")),
        "company": row.get("company") or "",
        "url": _as_text(row.get("url")),
        "published_at": row.get("published_at") or "",
        "policy_categories": categories,
        "intents": categories,
        "insurance_available": bool(row.get("insurance_available", False)),
        "insurance_type": row.get("insurance_type") or "",
        "compensation_limit": row.get("compensation_limit") or "",
        "claim_deadline": row.get("claim_deadline") or "",
        "source_path": str(DATASET_PATH),
    }


def main() -> None:
    """生成或续跑 policy embedding H5。"""
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_jsonl(DATASET_PATH)
    texts = [build_policy_text(row) for row in rows]
    metadata = [build_policy_metadata(row, index) for index, row in enumerate(rows)]
    h5_path = EMBEDDINGS_DIR / OUTPUT_FILENAME

    with h5py.File(h5_path, "a") as h5_file:
        print(f"开始编码 policy，样本数={len(texts)}")
        shape = encode_texts_to_h5(split_name=SPLIT_NAME, texts=texts, h5_file=h5_file)
        print(f"policy 编码完成，shape={shape}")

    save_json({SPLIT_NAME: metadata}, EMBEDDINGS_DIR / METADATA_FILENAME)
    print(f"已写入: {h5_path}")
    print(f"已写入: {EMBEDDINGS_DIR / METADATA_FILENAME}")


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_as_text(item) for item in value if _as_text(item)]


if __name__ == "__main__":
    main()
