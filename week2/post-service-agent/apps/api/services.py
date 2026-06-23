from __future__ import annotations

import json
from collections.abc import Iterator

from apps.core.models import Citation, Conversation, Message, Ticket
from post_ai.config import AppConfig
from post_ai.prompts import build_rag_messages
from post_ai.tickets import build_rule_based_ticket
from post_ai.vectorstores import FaissPostalIndex


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
        hits = _search_faiss_with_existing_vector(message)
        for hit in hits:
            yield {
                "event": "citation",
                "data": {
                    "rank": hit.rank,
                    "score": hit.score,
                    "source_key": hit.document.source_key,
                    "quoted_text": hit.document.content[:500],
                },
            }

    # 当前阶段不在测试里调用真实 Ollama。先返回可验证的 RAG preview，
    # 后续接 provider stream 时替换这里的 answer 生成来源。
    rag_messages = build_rag_messages(message, hits)
    answer = "已收到问题。当前已接入 Django 和 post_ai，RAG 引用已准备。"
    if hits:
        answer += f" 本次检索到 {len(hits)} 条邮政相关对话。"
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
            quoted_text=hit.document.content[:1000],
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

    yield {"event": "delta", "data": {"content": answer}}
    yield {"event": "ticket", "data": {"payload": ticket.model_dump()}}
    yield {"event": "done", "data": {"conversation_id": conversation.id, "message_id": assistant.id}}


def encode_sse(event: dict) -> str:
    return f"event: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"


def _search_faiss_with_existing_vector(query: str):
    artifact_dir = AppConfig.from_env().vector_store_settings.faiss_artifact_dir
    if artifact_dir is None or not (artifact_dir / "postal.faiss").exists():
        return []
    index = FaissPostalIndex.load(artifact_dir)
    # 旧 H5 没有 query embedding。这里用第一条向量维度构造稳定占位查询，
    # 只用于 Django 接线测试；真实查询后续走 qwen3 provider embedding。
    import numpy as np

    vector = np.ones(index.index.d, dtype="float32")
    return index.search(vector, top_k=3)


def _first_issue_type(hits) -> str:
    for hit in hits:
        intents = hit.document.metadata.get("intents") or []
        if intents:
            return intents[0]
    return ""
