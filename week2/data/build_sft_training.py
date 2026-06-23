#!/usr/bin/env python3
"""Build postal-related SFT splits from CSDS using LLM filter results."""

from __future__ import annotations

import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent
CSDS_DIR = DATA_DIR / "CSDS"
FILTER_PATH = DATA_DIR / "llm_filter" / "postal_filter_results.json"
OUTPUT_DIR = DATA_DIR / "sft_training"
SPLITS = ("train", "val", "test")


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def validate_match(split: str, sample: dict, row: dict) -> None:
    if sample.get("Session_id") != row.get("session_id"):
        raise ValueError(
            f"{split}[{row.get('index')}] session_id mismatch: "
            f"{sample.get('Session_id')} != {row.get('session_id')}"
        )
    if sample.get("DialogueID") != row.get("dialogue_id"):
        raise ValueError(
            f"{split}[{row.get('index')}] dialogue_id mismatch: "
            f"{sample.get('DialogueID')} != {row.get('dialogue_id')}"
        )


def build_split(split: str, filters: list[dict]) -> list[dict]:
    source = load_json(CSDS_DIR / f"{split}.json")
    if len(source) != len(filters):
        raise ValueError(
            f"{split} length mismatch: CSDS has {len(source)}, "
            f"filter has {len(filters)}"
        )

    selected = []
    for row in filters:
        index = row.get("index")
        if not isinstance(index, int) or index < 0 or index >= len(source):
            raise ValueError(f"{split} has invalid filter index: {index!r}")

        sample = source[index]
        validate_match(split, sample, row)

        if row.get("is_postal_related") is True:
            selected.append(sample)

    return selected


def main() -> None:
    filter_results = load_json(FILTER_PATH)

    summary = {}
    for split in SPLITS:
        selected = build_split(split, filter_results[split])
        save_json(OUTPUT_DIR / f"{split}.json", selected)
        summary[split] = {
            "source": len(filter_results[split]),
            "selected": len(selected),
            "output": str(OUTPUT_DIR / f"{split}.json"),
        }

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
