from __future__ import annotations

from datetime import datetime

from ninja import Schema


class ConversationOut(Schema):
    id: int
    title: str
    is_pinned: bool
    created_at: datetime
    updated_at: datetime


class ConversationCreateIn(Schema):
    title: str = ""


class MessageOut(Schema):
    id: int
    role: str
    content: str
    metadata: dict
    created_at: datetime


class MessageCreateIn(Schema):
    content: str


class ChatPreviewIn(Schema):
    conversation_id: int | None = None
    message: str
    use_rag: bool = True
    use_sft: bool = False
