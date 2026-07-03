from __future__ import annotations

import os
from pathlib import Path

import yaml

from src.schemas import AppConfig


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_SIZE = "3b"
CONFIG_ENV = "MICROSERVICE_CONFIG"
MODEL_SIZE_ENV = "MICROSERVICE_MODEL_SIZE"


def config_path_for_model_size(model_size: str) -> Path:
    normalized = model_size.strip().lower()
    if normalized not in {"3b", "7b"}:
        raise ValueError(f"Unsupported model size: {model_size}")
    return BASE_DIR / f"config_{normalized}.yaml"


def resolve_config_path() -> Path:
    explicit_path = os.getenv(CONFIG_ENV)
    if explicit_path:
        return Path(explicit_path).expanduser()
    return config_path_for_model_size(os.getenv(MODEL_SIZE_ENV, DEFAULT_MODEL_SIZE))


def load_config(path: Path | None = None) -> AppConfig:
    config_path = path or resolve_config_path()
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return AppConfig.model_validate(raw)
