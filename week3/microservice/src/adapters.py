from __future__ import annotations

import json
from pathlib import Path

from src.schemas import AppConfig


def resolve_adapter_path(config: AppConfig) -> Path:
    if config.model.adapter_path:
        adapter_path = Path(config.model.adapter_path).expanduser()
        if not adapter_path.exists():
            raise FileNotFoundError(f"Configured adapter path not found: {adapter_path}")
        return adapter_path

    run_dir = Path(config.model.runs_root).expanduser() / config.model.run_id
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")

    if config.model.rank is not None:
        rank_dir = run_dir / f"rank_{config.model.rank}"
        metadata_files = list(rank_dir.glob("logs/best_adapter_*.json"))
    else:
        metadata_files = list(run_dir.glob("rank_*/logs/best_adapter_*.json"))

    candidates: list[tuple[float, Path]] = []
    for result_file in metadata_files:
        try:
            payload = json.loads(result_file.read_text(encoding="utf-8"))
            best_score = float(payload["best_score"])
            best_adapter_path = Path(payload["best_adapter_path"]).expanduser()
        except Exception as exc:  # pragma: no cover - defensive path
            raise ValueError(f"Invalid best adapter metadata: {result_file}") from exc
        if best_adapter_path.exists():
            candidates.append((best_score, best_adapter_path))

    if not candidates:
        raise FileNotFoundError(f"No valid best adapter metadata found under: {run_dir}")

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]
