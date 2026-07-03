from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from src.api_types import ChatLogRecord


DEFAULT_LOG_DIR = Path(__file__).resolve().parents[1] / "logs" / "chat_requests"


class RequestLogger:
    def __init__(self, log_dir: Path = DEFAULT_LOG_DIR) -> None:
        self._log_dir = log_dir

    @property
    def log_dir(self) -> Path:
        return self._log_dir

    def write(self, record: ChatLogRecord) -> Path:
        self._log_dir.mkdir(parents=True, exist_ok=True)
        now = time.time()
        timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime(now))
        millisecond = int((now % 1) * 1000)
        model_id = _safe_filename(str(record.get("model", "unknown-model")))
        log_path = self._log_dir / f"{timestamp}_{millisecond:03d}_{model_id}.json"
        payload = {
            "logged_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            **record,
        }
        with log_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.write("\n")
        return log_path


def _safe_filename(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in value)
