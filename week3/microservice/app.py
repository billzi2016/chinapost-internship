#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Literal

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field


DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.yaml")


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 18731


class GenerationConfig(BaseModel):
    max_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.95


class ModelConfig(BaseModel):
    model_id: str = "qwen2.5-3b-lora-auto"
    model_path: str
    runs_root: str
    run_id: str
    system_prompt: str = (
        "你是一个专业、准确、克制的邮政客服助手。"
        "你可以帮助用户理解 EMS、中国邮政、包裹寄递、网点咨询、物流异常、禁限寄、时效和资费等问题。"
        "遇到需要实时查询、政策确认或个人信息核验的问题时，应建议用户通过官方渠道、运单号、网点或人工客服核实。"
        "不要编造赔付金额、具体时限、网点营业时间或官方承诺。"
    )


class AppConfig(BaseModel):
    server: ServerConfig
    model: ModelConfig
    generation: GenerationConfig


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage]
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    max_completion_tokens: int | None = None
    stream: bool = False


def chunk_text(text: str, chunk_size: int = 32) -> list[str]:
    return [text[index : index + chunk_size] for index in range(0, len(text), chunk_size)] or [""]


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return AppConfig.model_validate(raw)


def resolve_best_adapter(config: AppConfig) -> Path:
    run_dir = Path(config.model.runs_root).expanduser() / config.model.run_id
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")

    candidates: list[tuple[float, Path]] = []
    for result_file in run_dir.glob("rank_*/logs/best_adapter_*.json"):
        try:
            payload = json.loads(result_file.read_text(encoding="utf-8"))
            best_score = float(payload["best_score"])
            best_adapter_path = Path(payload["best_adapter_path"]).expanduser()
        except Exception as exc:  # pragma: no cover - defensive path
            raise ValueError(f"Invalid best adapter metadata: {result_file}") from exc
        if best_adapter_path.exists():
            candidates.append((best_score, best_adapter_path))

    if not candidates:
        raise FileNotFoundError(f"No valid best adapter metadata found under: {run_dir}")

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def load_tokenizer(model_path: str) -> Any | None:
    try:
        from transformers import AutoTokenizer
    except ImportError:
        return None

    try:
        return AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    except Exception:
        return None


def render_prompt(messages: list[dict[str, str]], tokenizer: Any | None) -> str:
    if tokenizer is not None and hasattr(tokenizer, "apply_chat_template"):
        try:
            return tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        except Exception:
            pass

    parts: list[str] = []
    for message in messages:
        parts.append(f"{message['role'].upper()}: {message['content'].strip()}")
    parts.append("ASSISTANT:")
    return "\n\n".join(parts)


def clean_generation_text(text: str) -> str:
    cleaned = text.strip()
    if "==========" in cleaned:
        parts = [part.strip() for part in cleaned.split("==========")]
        if len(parts) >= 2 and parts[1]:
            cleaned = parts[1]
    for prefix in ("Prompt: ", "Generation: ", "Peak memory: "):
        lines = [line for line in cleaned.splitlines() if not line.startswith(prefix)]
        cleaned = "\n".join(lines).strip()
    return cleaned.strip()


def build_messages(config: AppConfig, request: ChatCompletionRequest) -> list[dict[str, str]]:
    messages = [message.model_dump() for message in request.messages]
    if not any(message["role"] == "system" for message in messages):
        messages.insert(0, {"role": "system", "content": config.model.system_prompt})
    return messages


def generate_text(
    config: AppConfig,
    adapter_path: Path,
    prompt: str,
    temperature: float,
    top_p: float,
    max_tokens: int,
) -> str:
    command = [
        "mlx_lm.generate",
        "--model",
        config.model.model_path,
        "--max-tokens",
        str(max_tokens),
        "--temp",
        str(temperature),
        "--top-p",
        str(top_p),
        "--prompt",
        prompt,
    ]
    command.extend(["--adapter-path", str(adapter_path)])

    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr.strip() or "mlx_lm.generate failed")
    return clean_generation_text(result.stdout)


CONFIG = load_config()
TOKENIZER = load_tokenizer(CONFIG.model.model_path)
BEST_ADAPTER_PATH = resolve_best_adapter(CONFIG)
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
                "id": CONFIG.model.model_id,
                "object": "model",
                "owned_by": "local-mlx",
            }
        ],
    }


@app.post("/v1/chat/completions")
def chat_completions(request: ChatCompletionRequest) -> dict[str, Any]:
    if request.model and request.model != CONFIG.model.model_id:
        raise HTTPException(status_code=400, detail=f"Unknown model: {request.model}")
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")

    temperature = request.temperature if request.temperature is not None else CONFIG.generation.temperature
    top_p = request.top_p if request.top_p is not None else CONFIG.generation.top_p
    requested_max_tokens = request.max_completion_tokens
    if requested_max_tokens is None:
        requested_max_tokens = request.max_tokens
    max_tokens = requested_max_tokens if requested_max_tokens is not None else CONFIG.generation.max_tokens

    messages = build_messages(CONFIG, request)
    prompt = render_prompt(messages, TOKENIZER)
    content = generate_text(
        CONFIG,
        BEST_ADAPTER_PATH,
        prompt,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
    )

    prompt_tokens = max(1, len(prompt) // 4)
    completion_tokens = max(1, len(content) // 4)
    created = int(time.time())

    if request.stream:
        def event_stream() -> Any:
            first_chunk = {
                "id": f"chatcmpl-{uuid.uuid4().hex}",
                "object": "chat.completion.chunk",
                "created": created,
                "model": CONFIG.model.model_id,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant"},
                        "finish_reason": None,
                    }
                ],
            }
            yield f"data: {json.dumps(first_chunk, ensure_ascii=False)}\n\n"

            for piece in chunk_text(content):
                chunk = {
                    "id": f"chatcmpl-{uuid.uuid4().hex}",
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": CONFIG.model.model_id,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": piece},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

            final_chunk = {
                "id": f"chatcmpl-{uuid.uuid4().hex}",
                "object": "chat.completion.chunk",
                "created": created,
                "model": CONFIG.model.model_id,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop",
                    }
                ],
            }
            yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": created,
        "model": CONFIG.model.model_id,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "mlx-openai-compatible",
        "model": CONFIG.model.model_id,
        "config_path": str(DEFAULT_CONFIG_PATH),
        "best_adapter_path": str(BEST_ADAPTER_PATH),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=CONFIG.server.host,
        port=CONFIG.server.port,
        reload=False,
    )
