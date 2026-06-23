from __future__ import annotations

from datetime import datetime

from ninja import Schema


class ConversationOut(Schema):
    id: int
    title: str
    latest_error: str
    is_pinned: bool
    created_at: datetime
    updated_at: datetime


class ConversationCreateIn(Schema):
    title: str = ""


class CitationOut(Schema):
    score: float
    quoted_text: str
    metadata: dict


class MessageOut(Schema):
    id: int
    role: str
    content: str
    metadata: dict
    citations: list[CitationOut] = []
    created_at: datetime


class MessageCreateIn(Schema):
    content: str


class ChatPreviewIn(Schema):
    conversation_id: int | None = None
    message: str
    use_rag: bool = True
    use_sft: bool = False


class TicketOut(Schema):
    id: int
    payload: dict
    is_valid: bool
    validation_error: str


class ProviderHealthOut(Schema):
    chat_provider: str
    chat_model: str
    embedding_provider: str
    embedding_model: str
    vector_provider: str
    sft_configured: bool
