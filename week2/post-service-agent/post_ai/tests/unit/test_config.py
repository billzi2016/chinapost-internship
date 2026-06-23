from pathlib import Path

from post_ai.config import AppConfig


def test_config_loads_yaml_provider_and_vector_store_settings() -> None:
    config = AppConfig.from_yaml(Path("config/post_ai.yaml"))

    assert config.mode == "microservice"
    assert config.provider_settings.default_chat_provider == "ollama"
    assert config.provider_settings.default_embedding_model == "qwen3-embedding:8b"
    assert config.vector_store_settings.provider == "pgvector"
    assert config.vector_store_settings.faiss_artifact_dir is not None
    assert config.vector_store_settings.faiss_artifact_dir.name == "faiss"
    assert config.vector_store_settings.pgvector_table == "core_postalembedding"


def test_config_env_can_switch_vector_provider_to_faiss(monkeypatch) -> None:
    monkeypatch.setenv("POST_AI_VECTOR_PROVIDER", "faiss")

    config = AppConfig.from_yaml(Path("config/post_ai.yaml"))

    assert config.vector_store_settings.provider == "faiss"


def test_config_local_mode_defaults_vector_provider_to_faiss(monkeypatch) -> None:
    monkeypatch.setenv("POST_SERVICE_MODE", "local")
    monkeypatch.delenv("POST_AI_VECTOR_PROVIDER", raising=False)

    config = AppConfig.from_yaml(Path("config/post_ai.yaml"))

    assert config.mode == "local"
    assert config.vector_store_settings.provider == "faiss"


def test_config_microservice_mode_uses_mode_specific_vector_provider(monkeypatch) -> None:
    monkeypatch.setenv("POST_SERVICE_MODE", "microservice")
    monkeypatch.delenv("POST_AI_VECTOR_PROVIDER", raising=False)

    config = AppConfig.from_yaml(Path("config/post_ai.yaml"))

    assert config.mode == "microservice"
    assert config.vector_store_settings.provider == "pgvector"
