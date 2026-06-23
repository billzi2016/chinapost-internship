from __future__ import annotations

import json
from pathlib import Path

from post_ai.schemas import CSDSDialogue, SplitName


SPLITS: tuple[SplitName, ...] = ("train", "val", "test")


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
