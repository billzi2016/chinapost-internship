from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


DEFAULT_SYSTEM_PROMPT = (
    "你是一个专业、准确、克制的邮政客服助手。"
    "你可以帮助用户理解 EMS、中国邮政、包裹寄递、网点咨询、物流异常、禁限寄、时效和资费等问题。"
    "遇到需要实时查询、政策确认或个人信息核验的问题时，应建议用户通过官方渠道、运单号、网点或人工客服核实。"
    "不要编造赔付金额、具体时限、网点营业时间或官方承诺。"
)


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 18731


class GenerationConfig(BaseModel):
    max_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.95


class ModelConfig(BaseModel):
    model_id: str
    model_path: str
    runs_root: str
    run_id: str
    rank: int | None = None
    adapter_path: str | None = None
    knowledge_cutoff_date: str | None = None
    system_prompt: str = DEFAULT_SYSTEM_PROMPT


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
