from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


TEST_DIR = Path(__file__).resolve().parent
MICROSERVICE_DIR = TEST_DIR.parent
CONFIG_PATH = MICROSERVICE_DIR / "config.yaml"


def load_app_module():
    assert CONFIG_PATH.exists(), f"Missing config: {CONFIG_PATH}"

    if str(MICROSERVICE_DIR) not in sys.path:
        sys.path.insert(0, str(MICROSERVICE_DIR))

    if "app" in sys.modules:
        return importlib.reload(sys.modules["app"])
    return importlib.import_module("app")


def test_best_adapter_resolution() -> None:
    app_module = load_app_module()
    best_adapter = app_module.resolve_best_adapter(app_module.CONFIG)
    assert best_adapter.exists()
    assert best_adapter.is_dir()
    assert "best_adapter" in str(best_adapter)


def test_health_endpoint() -> None:
    app_module = load_app_module()
    client = TestClient(app_module.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_models_endpoint() -> None:
    app_module = load_app_module()
    client = TestClient(app_module.app)
    response = client.get("/v1/models")
    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "list"
    assert payload["data"][0]["id"] == app_module.CONFIG.model.model_id


def test_chat_completions_real_generation() -> None:
    app_module = load_app_module()
    client = TestClient(app_module.app)
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": app_module.CONFIG.model.model_id,
            "messages": [{"role": "user", "content": "用一句话回答：EMS是什么？"}],
            "max_completion_tokens": 48,
            "temperature": 0.2,
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["object"] == "chat.completion"
    assert payload["model"] == app_module.CONFIG.model.model_id
    assert payload["choices"][0]["message"]["role"] == "assistant"
    assert payload["choices"][0]["message"]["content"].strip()
    assert payload["usage"]["completion_tokens"] >= 1


def test_chat_completions_streaming_real_generation() -> None:
    app_module = load_app_module()
    client = TestClient(app_module.app)
    with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": app_module.CONFIG.model.model_id,
            "messages": [{"role": "user", "content": "简短回答：中国邮政能寄包裹吗？"}],
            "max_completion_tokens": 32,
            "temperature": 0.2,
            "stream": True,
        },
    ) as response:
        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith("text/event-stream")
        body = "".join(response.iter_text())

    assert "data: [DONE]" in body
    chunks = [line.removeprefix("data: ").strip() for line in body.splitlines() if line.startswith("data: {")]
    assert chunks, body
    decoded = [json.loads(chunk) for chunk in chunks]
    assert decoded[0]["object"] == "chat.completion.chunk"
    assert any(
        choice.get("delta", {}).get("content")
        for chunk in decoded
        for choice in chunk.get("choices", [])
    )
