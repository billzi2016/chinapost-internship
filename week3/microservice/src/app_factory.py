from __future__ import annotations

from src.adapters import resolve_adapter_path
from src.api import AppState, create_app
from src.config import load_config, resolve_config_path
from src.generation import MlxGenerator
from src.prompts import load_tokenizer
from src.request_logger import RequestLogger


def build_state() -> AppState:
    config_path = resolve_config_path()
    config = load_config(config_path)
    tokenizer = load_tokenizer(config.model.model_path)
    adapter_path = resolve_adapter_path(config)
    generator = MlxGenerator(config, adapter_path)
    request_logger = RequestLogger()
    return AppState(
        config=config,
        config_path=config_path,
        adapter_path=adapter_path,
        tokenizer=tokenizer,
        generator=generator,
        request_logger=request_logger,
    )


def build_app(state: AppState | None = None):
    return create_app(state or build_state())
