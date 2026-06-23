from pathlib import Path

from post_ai.config import AppConfig


def test_config_loads_yaml_provider_and_vector_store_settings() -> None:
    config = AppConfig.from_yaml(Path("config/post_ai.yaml"))

    assert config.provider_settings.default_chat_provider == "ollama"
    assert config.provider_settings.default_embedding_model == "qwen3-embedding:8b"
    assert config.vector_store_settings.provider == "faiss"
    assert config.vector_store_settings.faiss_artifact_dir is not None
    assert config.vector_store_settings.faiss_artifact_dir.name == "faiss"
