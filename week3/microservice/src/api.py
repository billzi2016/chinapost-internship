from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from src.generation import MlxGenerator
from src.prompts import build_messages, render_prompt
from src.request_logger import RequestLogger
from src.schemas import AppConfig, ChatCompletionRequest


@dataclass(frozen=True)
class AppState:
    config: AppConfig
    config_path: Path
    adapter_path: Path
    tokenizer: Any | None
    generator: MlxGenerator
    request_logger: RequestLogger


def chunk_text(text: str, chunk_size: int = 32) -> list[str]:
    return [text[index : index + chunk_size] for index in range(0, len(text), chunk_size)] or [""]


def create_app(state: AppState) -> FastAPI:
    app = FastAPI(title="MLX OpenAI-Compatible Microservice", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/models")
    def list_models() -> dict[str, Any]:
        return {
            "object": "list",
            "data": [
                {
                    "id": state.config.model.model_id,
                    "object": "model",
                    "owned_by": "local-mlx",
                }
            ],
        }

    @app.post("/v1/chat/completions")
    def chat_completions(request: ChatCompletionRequest) -> dict[str, Any]:
        started_at = time.time()
        if request.model and request.model != state.config.model.model_id:
            raise HTTPException(status_code=400, detail=f"Unknown model: {request.model}")
        if not request.messages:
            raise HTTPException(status_code=400, detail="messages must not be empty")

        temperature = request.temperature if request.temperature is not None else state.config.generation.temperature
        top_p = request.top_p if request.top_p is not None else state.config.generation.top_p
        requested_max_tokens = request.max_completion_tokens
        if requested_max_tokens is None:
            requested_max_tokens = request.max_tokens
        max_tokens = requested_max_tokens if requested_max_tokens is not None else state.config.generation.max_tokens

        messages = build_messages(state.config, request)
        prompt = render_prompt(messages, state.tokenizer)
        content = state.generator.generate(prompt, temperature=temperature, top_p=top_p, max_tokens=max_tokens)

        prompt_tokens = max(1, len(prompt) // 4)
        completion_tokens = max(1, len(content) // 4)
        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }
        created = int(time.time())
        state.request_logger.write(
            {
                "created": created,
                "model": state.config.model.model_id,
                "config_path": str(state.config_path),
                "adapter_path": str(state.adapter_path),
                "stream": request.stream,
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens,
                "messages": messages,
                "assistant_content": content,
                "usage": usage,
                "latency_seconds": round(time.time() - started_at, 4),
            }
        )

        if request.stream:
            def event_stream() -> Any:
                first_chunk = {
                    "id": f"chatcmpl-{uuid.uuid4().hex}",
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": state.config.model.model_id,
                    "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
                }
                yield f"data: {json.dumps(first_chunk, ensure_ascii=False)}\n\n"

                for piece in chunk_text(content):
                    chunk = {
                        "id": f"chatcmpl-{uuid.uuid4().hex}",
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": state.config.model.model_id,
                        "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}],
                    }
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

                final_chunk = {
                    "id": f"chatcmpl-{uuid.uuid4().hex}",
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": state.config.model.model_id,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
                yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(event_stream(), media_type="text/event-stream")

        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": created,
            "model": state.config.model.model_id,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                **usage,
            },
        }

    @app.get("/")
    def root() -> dict[str, Any]:
        return {
            "service": "mlx-openai-compatible",
            "model": state.config.model.model_id,
            "config_path": str(state.config_path),
            "adapter_path": str(state.adapter_path),
            "log_dir": str(state.request_logger.log_dir),
        }

    return app
