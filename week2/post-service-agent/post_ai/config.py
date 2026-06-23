from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEEK2_ROOT = PROJECT_ROOT.parent
DEFAULT_DATA_DIR = WEEK2_ROOT / "data"
DEFAULT_ARTIFACT_DIR = PROJECT_ROOT / "artifacts"


@dataclass(frozen=True)
class DataPaths:
    data_dir: Path = DEFAULT_DATA_DIR

    @property
    def csds_dir(self) -> Path:
        return self.data_dir / "CSDS"

    @property
    def filter_path(self) -> Path:
        return self.data_dir / "llm_filter" / "postal_filter_results.json"

    @property
    def embedding_metadata_path(self) -> Path:
        return self.data_dir / "embeddings" / "dialogue_metadata.json"

    @property
    def old_embedding_h5_path(self) -> Path:
        return self.data_dir / "embeddings" / "dialogue_embeddings.h5"


@dataclass(frozen=True)
class ProviderSettings:
    default_chat_provider: str = "ollama"
    default_embedding_provider: str = "ollama"
    default_chat_model: str = "gpt-oss:20b"
    default_embedding_model: str = "qwen3-embedding:8b"
    ollama_base_url: str = "http://localhost:11434"
    vllm_base_url: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_api_key: str | None = None
    fastapi_base_url: str | None = None
    sft_provider: str | None = None
    sft_model: str | None = None

    @classmethod
    def from_env(cls) -> "ProviderSettings":
        return cls(
            default_chat_provider=os.getenv("POST_AI_CHAT_PROVIDER", "ollama"),
            default_embedding_provider=os.getenv("POST_AI_EMBEDDING_PROVIDER", "ollama"),
            default_chat_model=os.getenv("POST_AI_CHAT_MODEL", "gpt-oss:20b"),
            default_embedding_model=os.getenv("POST_AI_EMBEDDING_MODEL", "qwen3-embedding:8b"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            vllm_base_url=os.getenv("VLLM_BASE_URL"),
            openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
            fastapi_base_url=os.getenv("SFT_FASTAPI_BASE_URL"),
            sft_provider=os.getenv("SFT_PROVIDER"),
            sft_model=os.getenv("SFT_MODEL"),
        )


@dataclass(frozen=True)
class AppConfig:
    data_paths: DataPaths
    provider_settings: ProviderSettings
    artifact_dir: Path = DEFAULT_ARTIFACT_DIR

    @classmethod
    def from_env(cls) -> "AppConfig":
        data_dir = Path(os.getenv("POST_AI_DATA_DIR", str(DEFAULT_DATA_DIR))).expanduser()
        artifact_dir = Path(os.getenv("POST_AI_ARTIFACT_DIR", str(DEFAULT_ARTIFACT_DIR))).expanduser()
        return cls(
            data_paths=DataPaths(data_dir=data_dir),
            provider_settings=ProviderSettings.from_env(),
            artifact_dir=artifact_dir,
        )
