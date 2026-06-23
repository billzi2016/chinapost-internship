from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from post_ai.providers.base import ModelProvider, ProviderError
from post_ai.schemas import ChatDelta, ChatMessage, ChatResult, EmbeddingResult


class OllamaProvider(ModelProvider):
    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", timeout: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def chat(
        self,
        messages: list[ChatMessage],
        model: str,
        options: dict[str, Any] | None = None,
    ) -> ChatResult:
        payload = {
            "model": model,
            "messages": [message.model_dump() for message in messages],
            "stream": False,
            "options": options or {},
        }
        data = self._post_json("/api/chat", payload)
        content = data.get("message", {}).get("content", "")
        return ChatResult(content=content, raw=data)

    def stream_chat(
        self,
        messages: list[ChatMessage],
        model: str,
        options: dict[str, Any] | None = None,
    ) -> Iterator[ChatDelta]:
        payload = {
            "model": model,
            "messages": [message.model_dump() for message in messages],
            "stream": True,
            "options": options or {},
        }
        request = self._request("/api/chat", payload)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    yield ChatDelta(
                        content=data.get("message", {}).get("content", ""),
                        done=bool(data.get("done", False)),
                        raw=data,
                    )
        except URLError as exc:
            raise ProviderError(f"Ollama stream request failed: {exc}") from exc

    def embed(
        self,
        texts: list[str],
        model: str,
        options: dict[str, Any] | None = None,
    ) -> EmbeddingResult:
        payload = {
            "model": model,
            "input": texts,
            "options": options or {},
        }
        data = self._post_json("/api/embed", payload)
        vectors = data.get("embeddings")
        if vectors is None and "embedding" in data:
            vectors = [data["embedding"]]
        if not isinstance(vectors, list):
            raise ProviderError("Ollama embed response did not contain embeddings.")
        return EmbeddingResult(vectors=vectors, model=model, provider=self.name, raw=data)

    def is_available(self, model: str) -> bool:
        try:
            data = self._post_json("/api/show", {"model": model})
        except ProviderError:
            return False
        return bool(data)

    def _request(self, path: str, payload: dict[str, Any]) -> Request:
        body = json.dumps(payload).encode("utf-8")
        return Request(
            self.base_url + path,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = self._request(path, payload)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (URLError, json.JSONDecodeError) as exc:
            raise ProviderError(f"Ollama request failed for {path}: {exc}") from exc
