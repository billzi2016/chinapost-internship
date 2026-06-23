from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from post_ai.providers.base import ModelProvider, ProviderError, ProviderUnavailableError
from post_ai.schemas import ChatDelta, ChatMessage, ChatResult, EmbeddingResult


class OpenAICompatibleProvider(ModelProvider):
    def __init__(
        self,
        name: str,
        base_url: str | None,
        api_key: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/") if base_url else None
        self.api_key = api_key
        self.timeout = timeout

    def chat(
        self,
        messages: list[ChatMessage],
        model: str,
        options: dict[str, Any] | None = None,
    ) -> ChatResult:
        self._ensure_configured()
        payload = {
            "model": model,
            "messages": [message.model_dump() for message in messages],
            "stream": False,
            **(options or {}),
        }
        data = self._post_json("/chat/completions", payload)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return ChatResult(content=content, raw=data)

    def stream_chat(
        self,
        messages: list[ChatMessage],
        model: str,
        options: dict[str, Any] | None = None,
    ) -> Iterator[ChatDelta]:
        self._ensure_configured()
        payload = {
            "model": model,
            "messages": [message.model_dump() for message in messages],
            "stream": True,
            **(options or {}),
        }
        request = self._request("/chat/completions", payload)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if not line.startswith("data: "):
                        continue
                    data_text = line.removeprefix("data: ").strip()
                    if data_text == "[DONE]":
                        yield ChatDelta(content="", done=True, raw={})
                        break
                    data = json.loads(data_text)
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    yield ChatDelta(content=delta.get("content", ""), raw=data)
        except (URLError, json.JSONDecodeError) as exc:
            raise ProviderError(f"{self.name} stream request failed: {exc}") from exc

    def embed(
        self,
        texts: list[str],
        model: str,
        options: dict[str, Any] | None = None,
    ) -> EmbeddingResult:
        self._ensure_configured()
        payload = {"model": model, "input": texts, **(options or {})}
        data = self._post_json("/embeddings", payload)
        vectors = [item["embedding"] for item in data.get("data", [])]
        return EmbeddingResult(vectors=vectors, model=model, provider=self.name, raw=data)

    def is_available(self, model: str) -> bool:
        return bool(self.base_url and model)

    def _ensure_configured(self) -> None:
        if not self.base_url:
            raise ProviderUnavailableError(f"Provider '{self.name}' has no base URL configured.")

    def _request(self, path: str, payload: dict[str, Any]) -> Request:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return Request(
            self.base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = self._request(path, payload)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (URLError, json.JSONDecodeError) as exc:
            raise ProviderError(f"{self.name} request failed for {path}: {exc}") from exc
