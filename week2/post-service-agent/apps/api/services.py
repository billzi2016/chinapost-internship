from __future__ import annotations

import json
import re
from collections.abc import Iterator

from django.conf import settings

from apps.core.models import Citation, Conversation, Message, Ticket
from post_ai.config import AppConfig
from post_ai.pipeline import query_configured_vector_store
from post_ai.prompts import build_rag_messages, build_title_messages
from post_ai.providers import ProviderError, build_default_registry
from post_ai.tickets import build_rule_based_ticket
from post_ai.vectorstores import VectorStoreError


def create_conversation(title: str = "") -> Conversation:
    return Conversation.objects.create(title=title)


def get_or_create_conversation(conversation_id: int | None) -> Conversation:
    if conversation_id:
        return Conversation.objects.get(pk=conversation_id)
    return create_conversation()


def stream_chat_events(
    conversation_id: int | None,
    message: str,
    use_rag: bool,
    use_sft: bool,
) -> Iterator[dict]:
    conversation = get_or_create_conversation(conversation_id)
    Message.objects.create(conversation=conversation, role=Message.ROLE_USER, content=message)
    yield {
        "event": "meta",
        "data": {
            "conversation_id": conversation.id,
            "use_rag": use_rag,
            "use_sft": use_sft,
        },
    }

    if use_sft:
        yield {"event": "error", "data": {"message": "当前不存在 SFT 模型"}}
        return

    hits = []
    if use_rag:
        try:
            hits = query_configured_vector_store(message, top_k=3)
        except (ProviderError, VectorStoreError, ValueError) as exc:
            yield {
                "event": "error",
                "data": {
                    "message": f"RAG 检索失败：{exc}",
                },
            }
            return
        for hit in hits:
            quoted_text = normalize_display_text(hit.document.content[:500])
            yield {
                "event": "citation",
                "data": {
                    "rank": hit.rank,
                    "score": hit.score,
                    "source_key": hit.document.source_key,
                    "quoted_text": quoted_text,
                },
            }

    rag_messages = build_rag_messages(message, hits)
    try:
        answer = ""
        for content in _stream_assistant_answer(rag_messages):
            answer += content
            if content:
                yield {"event": "delta", "data": {"content": content}}
    except ProviderError as exc:
        yield {"event": "error", "data": {"message": f"模型生成失败：{exc}"}}
        return

    assistant = Message.objects.create(
        conversation=conversation,
        role=Message.ROLE_ASSISTANT,
        content=answer,
        metadata={"rag_prompt": [item.model_dump() for item in rag_messages]},
    )

    for hit in hits:
        Citation.objects.create(
            message=assistant,
            score=hit.score,
            quoted_text=normalize_display_text(hit.document.content[:1000]),
            metadata=hit.document.metadata,
        )

    ticket = build_rule_based_ticket(
        user_request=message,
        summary=answer,
        issue_type=_first_issue_type(hits),
        need_follow_up=False,
    )
    Ticket.objects.create(
        conversation=conversation,
        message=assistant,
        payload=ticket.model_dump(),
        is_valid=True,
    )
    _ensure_conversation_title(conversation, message, answer)

    yield {"event": "ticket", "data": {"payload": ticket.model_dump()}}
    yield {"event": "done", "data": {"conversation_id": conversation.id, "message_id": assistant.id}}


def encode_sse(event: dict) -> str:
    return f"event: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"


def _first_issue_type(hits) -> str:
    for hit in hits:
        intents = hit.document.metadata.get("intents") or []
        if intents:
            return intents[0]
    return ""


def normalize_display_text(text: str) -> str:
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    text = re.sub(r"\s+([，。！？；：、“”）])", r"\1", text)
    text = re.sub(r"([，。！？；：、“”])\s+(?=[\u4e00-\u9fff])", r"\1", text)
    text = re.sub(r"([（“])\s+", r"\1", text)
    return text


def _stream_assistant_answer(messages) -> Iterator[str]:
    if settings.POST_SERVICE_FAKE_LLM:
        yield "已收到问题。当前已接入 Django 和 post_ai。"
        return

    app_config = AppConfig.from_env()
    provider_settings = app_config.provider_settings
    registry = build_default_registry(provider_settings)
    provider = registry.get(provider_settings.default_chat_provider)
    for delta in provider.stream_chat(
        messages=messages,
        model=provider_settings.default_chat_model,
    ):
        if delta.content:
            yield delta.content


def _ensure_conversation_title(conversation: Conversation, user_message: str, answer: str) -> None:
    if conversation.title:
        return

    if settings.POST_SERVICE_FAKE_LLM:
        conversation.title = user_message[:20] or "未命名会话"
        conversation.save(update_fields=["title", "updated_at"])
        return

    app_config = AppConfig.from_env()
    provider_settings = app_config.provider_settings
    provider = build_default_registry(provider_settings).get(provider_settings.default_chat_provider)
    result = provider.chat(
        messages=build_title_messages(f"用户：{user_message}\n助手：{answer}"),
        model=provider_settings.default_chat_model,
    )
    title = result.content.strip().strip('"').strip("'")[:20]
    conversation.title = title or "未命名会话"
    conversation.save(update_fields=["title", "updated_at"])
