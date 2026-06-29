#!/usr/bin/env python3
"""合并 final-result/raw-josnl 下的 JSONL 文件到 dataset.jsonl。"""

from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "raw-josnl"
OUTPUT_PATH = BASE_DIR / "dataset.jsonl"

INPUT_FILES = [
    "training_samples.jsonl",
    "training_playwright_samples.jsonl",
]


def iter_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line for line in lines if line.strip()]


def main() -> int:
    merged_lines: list[str] = []

    for name in INPUT_FILES:
        path = INPUT_DIR / name
        merged_lines.extend(iter_lines(path))

    OUTPUT_PATH.write_text("\n".join(merged_lines) + ("\n" if merged_lines else ""), encoding="utf-8")
    print(f"wrote {len(merged_lines)} records to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
