from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from post_ai.env import load_env_file


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEEK2_ROOT = PROJECT_ROOT.parent
DEFAULT_DATA_DIR = WEEK2_ROOT / "data"
DEFAULT_ARTIFACT_DIR = PROJECT_ROOT / "artifacts"
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "post_ai.yaml"
load_env_file(PROJECT_ROOT / ".env")


def _resolve_project_path(value: str | None, default: Path | None = None) -> Path | None:
    if not value:
        return default
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    return path


def _load_yaml_config(path: Path) -> dict:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def _normalize_mode(value: str | None) -> str:
    mode = (value or "local").strip().lower()
    if mode not in {"local", "microservice"}:
        raise ValueError(f"Unsupported POST_SERVICE_MODE: {value!r}. Expected local or microservice.")
    return mode


def _default_vector_provider_for_mode(mode: str) -> str:
    return "faiss" if mode == "local" else "pgvector"


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

    @property
    def policy_dataset_jsonl_path(self) -> Path:
        return self.data_dir / "dataset.jsonl"

    @property
    def policy_embedding_metadata_path(self) -> Path:
        return self.data_dir / "embeddings" / "policy_metadata.json"

    @property
    def policy_embedding_h5_path(self) -> Path:
        return self.data_dir / "embeddings" / "policy_embeddings.h5"


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
    def from_mapping(cls, data: dict) -> "ProviderSettings":
        models = data.get("models", {})
        providers = data.get("providers", {})
        chat = models.get("chat", {})
        embedding = models.get("embedding", {})
        sft = models.get("sft", {})
        ollama = providers.get("ollama", {})
        vllm = providers.get("vllm", {})
        openrouter = providers.get("openrouter", {})
        fastapi = providers.get("fastapi", {})
        return cls(
            default_chat_provider=os.getenv("POST_AI_CHAT_PROVIDER") or chat.get("provider") or "ollama",
            default_embedding_provider=os.getenv("POST_AI_EMBEDDING_PROVIDER") or embedding.get("provider") or "ollama",
            default_chat_model=os.getenv("POST_AI_CHAT_MODEL") or chat.get("model") or "gpt-oss:20b",
            default_embedding_model=os.getenv("POST_AI_EMBEDDING_MODEL") or embedding.get("model") or "qwen3-embedding:8b",
            ollama_base_url=os.getenv("OLLAMA_BASE_URL") or ollama.get("base_url") or "http://localhost:11434",
            vllm_base_url=os.getenv("VLLM_BASE_URL") or vllm.get("base_url"),
            openrouter_base_url=os.getenv("OPENROUTER_BASE_URL") or openrouter.get("base_url") or "https://openrouter.ai/api/v1",
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY") or openrouter.get("api_key"),
            fastapi_base_url=os.getenv("SFT_FASTAPI_BASE_URL") or fastapi.get("base_url"),
            sft_provider=os.getenv("SFT_PROVIDER") or sft.get("provider"),
            sft_model=os.getenv("SFT_MODEL") or sft.get("model"),
        )

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
class VectorStoreSettings:
    provider: str = "pgvector"
    faiss_artifact_dir: Path | None = DEFAULT_ARTIFACT_DIR / "faiss"
    faiss_index_file: str = "postal.faiss"
    faiss_metadata_file: str = "postal_metadata.json"
    pgvector_dsn: str | None = None
    pgvector_table: str = "core_postalembedding"

    @classmethod
    def from_mapping(cls, data: dict, mode: str) -> "VectorStoreSettings":
        mode_settings = data.get("modes", {}).get(mode, {})
        vector = data.get("vector_store", {})
        faiss = vector.get("faiss", {})
        pgvector = vector.get("pgvector", {})
        return cls(
            provider=os.getenv("POST_AI_VECTOR_PROVIDER")
            or mode_settings.get("vector_store", {}).get("provider")
            or _default_vector_provider_for_mode(mode),
            faiss_artifact_dir=_resolve_project_path(
                os.getenv("POST_AI_FAISS_ARTIFACT_DIR") or faiss.get("artifact_dir"),
                DEFAULT_ARTIFACT_DIR / "faiss",
            ),
            faiss_index_file=faiss.get("index_file") or "postal.faiss",
            faiss_metadata_file=faiss.get("metadata_file") or "postal_metadata.json",
            pgvector_dsn=os.getenv("POST_AI_PGVECTOR_DSN") or pgvector.get("dsn") or build_pgvector_dsn_from_env(),
            pgvector_table=os.getenv("POST_AI_PGVECTOR_TABLE") or pgvector.get("table") or "core_postalembedding",
        )


@dataclass(frozen=True)
class AppConfig:
    mode: str
    data_paths: DataPaths
    provider_settings: ProviderSettings
    vector_store_settings: VectorStoreSettings
    artifact_dir: Path = DEFAULT_ARTIFACT_DIR

    @classmethod
    def from_yaml(cls, path: Path = DEFAULT_CONFIG_PATH) -> "AppConfig":
        data = _load_yaml_config(path)
        mode = _normalize_mode(os.getenv("POST_SERVICE_MODE") or data.get("mode"))
        data_dir = _resolve_project_path(data.get("data", {}).get("data_dir"), DEFAULT_DATA_DIR)
        artifact_dir = _resolve_project_path(
            data.get("artifacts", {}).get("artifact_dir"),
            DEFAULT_ARTIFACT_DIR,
        )
        assert data_dir is not None
        assert artifact_dir is not None
        return cls(
            mode=mode,
            data_paths=DataPaths(data_dir=data_dir),
            provider_settings=ProviderSettings.from_mapping(data),
            vector_store_settings=VectorStoreSettings.from_mapping(data, mode),
            artifact_dir=artifact_dir,
        )

    @classmethod
    def from_env(cls) -> "AppConfig":
        if DEFAULT_CONFIG_PATH.exists() and not os.getenv("POST_AI_IGNORE_YAML"):
            return cls.from_yaml(DEFAULT_CONFIG_PATH)
        data_dir = Path(os.getenv("POST_AI_DATA_DIR", str(DEFAULT_DATA_DIR))).expanduser()
        artifact_dir = Path(os.getenv("POST_AI_ARTIFACT_DIR", str(DEFAULT_ARTIFACT_DIR))).expanduser()
        mode = _normalize_mode(os.getenv("POST_SERVICE_MODE"))
        return cls(
            mode=mode,
            data_paths=DataPaths(data_dir=data_dir),
            provider_settings=ProviderSettings.from_env(),
            vector_store_settings=VectorStoreSettings(
                provider=os.getenv("POST_AI_VECTOR_PROVIDER") or _default_vector_provider_for_mode(mode),
                faiss_artifact_dir=Path(
                    os.getenv("POST_AI_FAISS_ARTIFACT_DIR", str(DEFAULT_ARTIFACT_DIR / "faiss"))
                ).expanduser(),
                pgvector_dsn=os.getenv("POST_AI_PGVECTOR_DSN") or build_pgvector_dsn_from_env(),
                pgvector_table=os.getenv("POST_AI_PGVECTOR_TABLE", "core_postalembedding"),
            ),
            artifact_dir=artifact_dir,
        )


def build_pgvector_dsn_from_env() -> str:
    user = os.getenv("DJANGO_DB_USER", "post_service")
    password = os.getenv("DJANGO_DB_PASSWORD", "post_service")
    host = os.getenv("DJANGO_DB_HOST", "127.0.0.1")
    port = os.getenv("DJANGO_DB_PORT", "5432")
    name = os.getenv("DJANGO_DB_NAME", "post_service_agent")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"
