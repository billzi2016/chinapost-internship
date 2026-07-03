from __future__ import annotations

import subprocess
from pathlib import Path

from fastapi import HTTPException

from src.prompts import clean_generation_text
from src.schemas import AppConfig


class MlxGenerator:
    def __init__(self, config: AppConfig, adapter_path: Path | None) -> None:
        self._config = config
        self._adapter_path = adapter_path

    def generate(
        self,
        prompt: str,
        temperature: float,
        top_p: float,
        max_tokens: int,
    ) -> str:
        command = [
            "mlx_lm.generate",
            "--model",
            self._config.model.model_path,
            "--max-tokens",
            str(max_tokens),
            "--temp",
            str(temperature),
            "--top-p",
            str(top_p),
            "--prompt",
            prompt,
        ]
        if self._adapter_path is not None:
            command.extend(["--adapter-path", str(self._adapter_path)])

        result = subprocess.run(command, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=result.stderr.strip() or "mlx_lm.generate failed")
        return clean_generation_text(result.stdout)
