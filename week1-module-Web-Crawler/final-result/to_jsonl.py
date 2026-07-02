#!/usr/bin/env python3
"""将 dataset-playwright/MCP-raw 下的 Markdown 整理为训练样本 JSONL。"""

from __future__ import annotations

import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "dataset-playwright" / "MCP-raw"
OUTPUT_PATH = BASE_DIR / "raw-josnl" / "training_playwright_samples.jsonl"

SOURCE_ID = "playwright_mcp"
COMPANY = "playwright_mcp"


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_line(line: str) -> str:
    line = line.strip()
    if not line:
        return ""
    if line in {"---", "***", "___"}:
        return ""
    if line.startswith(">"):
        line = line[1:].strip()
    line = re.sub(r"^\s*[-*]\s+", "", line)
    line = re.sub(r"^\s*\d+\.\s+", "", line)
    return line.strip()


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "section"


def split_sections(text: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    current_title = ""
    current_lines: list[str] = []

    for raw_line in text.splitlines():
        if raw_line.startswith("### "):
            if current_title:
                sections.append((current_title, current_lines))
            current_title = raw_line[4:].strip()
            current_lines = []
            continue
        if raw_line.startswith("## "):
            if current_title:
                sections.append((current_title, current_lines))
                current_title = ""
                current_lines = []
            continue
        if current_title:
            current_lines.append(raw_line)

    if current_title:
        sections.append((current_title, current_lines))
    return sections


def extract_category(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("## "):
            title = line[3:].strip()
            title = re.sub(r"^第[一二三四五六七八九十0-9]+部分[:：]\s*", "", title)
            return title
    return "playwright_dataset"


def build_summary(lines: list[str]) -> str:
    cleaned = [clean_line(line) for line in lines]
    cleaned = [line for line in cleaned if line]
    if not cleaned:
        return ""
    summary = " ".join(cleaned[:4])
    return normalize_whitespace(summary)


def build_evidence(lines: list[str]) -> str:
    cleaned = [clean_line(line) for line in lines]
    cleaned = [line for line in cleaned if line]
    return normalize_whitespace("\n".join(cleaned))


def iter_markdown_files() -> list[Path]:
    return sorted(INPUT_DIR.glob("*.md"), key=lambda path: path.name)


def build_record(path: Path, category: str, section_title: str, lines: list[str]) -> dict[str, object]:
    relative_path = path.relative_to(BASE_DIR)
    anchor = slugify(section_title)
    evidence_text = build_evidence(lines)
    summary = build_summary(lines)

    return {
        "source_id": SOURCE_ID,
        "company": COMPANY,
        "uri": f"{relative_path.as_posix()}#{anchor}",
        "title": section_title,
        "published_at": "",
        "policy_categories": [category],
        "summary": summary,
        "evidence_text": evidence_text,
        "insurance_available": False,
        "insurance_type": "未知",
        "compensation_limit": "",
        "claim_deadline": "",
        "requirements": [],
        "insurance_exclusions": [],
    }


def main() -> int:
    records: list[dict[str, object]] = []

    for path in iter_markdown_files():
        text = path.read_text(encoding="utf-8")
        category = extract_category(text)
        for section_title, lines in split_sections(text):
            record = build_record(path, category, section_title, lines)
            if record["summary"] or record["evidence_text"]:
                records.append(record)

    with OUTPUT_PATH.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False))
            fh.write("\n")

    print(f"wrote {len(records)} records to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
