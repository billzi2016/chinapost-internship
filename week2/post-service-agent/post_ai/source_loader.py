from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from post_ai.schemas import CSDSDialogue, PostalDocument, SplitName


SPLITS: tuple[SplitName, ...] = ("train", "val", "test")
POLICY_SPLIT: SplitName = "policy"


class DataFormatError(ValueError):
    pass


def split_path(csds_dir: Path, split: SplitName) -> Path:
    return csds_dir / f"{split}.json"


def load_csds_split(csds_dir: Path, split: SplitName) -> list[CSDSDialogue]:
    path = split_path(csds_dir, split)
    if path.name.startswith("._"):
        raise DataFormatError(f"AppleDouble file is not a CSDS data file: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise DataFormatError(f"CSDS split must be a JSON array: {path}")
    return [CSDSDialogue.model_validate(item) for item in raw]


def load_all_csds(csds_dir: Path) -> dict[SplitName, list[CSDSDialogue]]:
    return {split: load_csds_split(csds_dir, split) for split in SPLITS}


def load_policy_jsonl(path: Path) -> list[PostalDocument]:
    """读取爬虫最终产出的政策/FAQ JSONL，并映射成统一 RAG 文档。

    `dataset.jsonl` 不属于 CSDS 对话数据，也没有旧 H5 embedding，所以这里给它单独的
    `policy` split。后续 pgvector/FAISS 会用当前 embedding provider 为这些文档生成向量。
    """
    if not path.exists():
        return []

    documents: list[PostalDocument] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise DataFormatError(f"Policy JSONL line must be an object: {path}:{line_number + 1}")
        documents.append(build_policy_document(raw, path, line_number))
    return documents


def build_policy_document(raw: dict[str, Any], source_path: Path, index: int) -> PostalDocument:
    """把一条政策/FAQ 记录压成适合 embedding 的文本。"""
    source_id = _as_text(raw.get("source_id")) or "policy_dataset"
    title = _as_text(raw.get("title"))
    summary = _as_text(raw.get("summary"))
    evidence_text = _as_text(raw.get("evidence_text"))
    url = _as_text(raw.get("url"))
    categories = _as_text_list(raw.get("policy_categories"))
    requirements = _as_text_list(raw.get("requirements"))
    exclusions = _as_text_list(raw.get("insurance_exclusions"))

    content_parts = [
        f"资料来源: {raw.get('company') or '中国邮政/EMS'}",
        f"标题: {title}",
        f"政策分类: {'、'.join(categories)}",
        f"摘要: {summary}",
        f"证据原文: {evidence_text}",
    ]
    if requirements:
        content_parts.append(f"办理要求: {'、'.join(requirements)}")
    if raw.get("compensation_limit"):
        content_parts.append(f"赔付上限: {raw['compensation_limit']}")
    if raw.get("claim_deadline"):
        content_parts.append(f"理赔时限: {raw['claim_deadline']}")
    if exclusions:
        content_parts.append(f"保价除外责任: {'、'.join(exclusions)}")
    if url:
        content_parts.append(f"来源链接: {url}")

    metadata = {
        "split": POLICY_SPLIT,
        "index": index,
        "source_kind": "policy_jsonl",
        "source_id": source_id,
        "turn_count": 1,
        "title": title,
        "company": raw.get("company") or "",
        "url": url,
        "published_at": raw.get("published_at") or "",
        "policy_categories": categories,
        "intents": categories,
        "insurance_available": bool(raw.get("insurance_available", False)),
        "insurance_type": raw.get("insurance_type") or "",
        "compensation_limit": raw.get("compensation_limit") or "",
        "claim_deadline": raw.get("claim_deadline") or "",
        "source_path": str(source_path),
    }
    return PostalDocument(
        split=POLICY_SPLIT,
        index=index,
        session_id=f"{source_id}:{index}",
        dialogue_id=index,
        source_path=str(source_path),
        content="\n".join(part for part in content_parts if part.strip()),
        metadata=metadata,
    )


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_as_text(item) for item in value if _as_text(item)]
