"""API 请求与响应 schema。

本文件只定义 HTTP 边界的数据形状，避免路由函数和业务 service 里散落 dict 字段。
这些 schema 由 django-ninja 使用，会同时影响运行时校验和 OpenAPI 文档。
"""

from __future__ import annotations

from datetime import datetime

from ninja import Schema


class ConversationOut(Schema):
    """侧边栏会话列表项。"""

    id: int
    title: str
    latest_error: str
    is_pinned: bool
    created_at: datetime
    updated_at: datetime


class ConversationCreateIn(Schema):
    """创建会话请求。title 允许为空，后续可由首轮问题或标题模型补齐。"""

    title: str = ""


class CitationOut(Schema):
    """助手消息引用的检索来源。"""

    score: float
    quoted_text: str
    metadata: dict


class MessageOut(Schema):
    """历史消息响应。

    助手消息可能带 citations；用户消息和系统错误消息通常为空列表。
    """

    id: int
    role: str
    content: str
    metadata: dict
    citations: list[CitationOut] = []
    created_at: datetime


class MessageCreateIn(Schema):
    """追加普通用户消息的请求体。"""

    content: str


class ChatPreviewIn(Schema):
    """发起聊天 SSE 请求的请求体。

    `use_rag` 和 `use_sft` 是两个正交开关：
    - RAG 控制是否检索知识库；
    - SFT 控制是否用微调模型生成。
    """

    conversation_id: int | None = None
    message: str
    use_rag: bool = True
    use_sft: bool = False


class RetryLastMessageIn(Schema):
    """修改或重新回答最后一条用户消息的请求体。"""

    message_id: int
    message: str
    use_rag: bool = True
    use_sft: bool = False


class TicketOut(Schema):
    """工单响应结构。payload 是业务 JSON，具体字段由 `post_ai.tickets` 定义。"""

    id: int
    payload: dict
    is_valid: bool
    validation_error: str


class ProviderHealthOut(Schema):
    """前端 provider health 状态条的响应结构。"""

    chat_provider: str
    chat_model: str
    embedding_provider: str
    embedding_model: str
    vector_provider: str
    sft_configured: bool
