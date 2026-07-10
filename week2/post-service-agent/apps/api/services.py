"""Django API 的业务编排层。

这个文件不直接定义 HTTP 路由，也不直接写前端展示逻辑；它负责把一次聊天请求拆成：
1. 会话和消息落库；
2. 可选 RAG 检索；
3. 可选 SFT/LoRA 模型选择；
4. SSE 事件流输出；
5. 引用、标题和工单数据的持久化。

维护约定：
- RAG 和 SFT 是两个正交开关，不能互相覆盖。
- Provider 调用必须走 `post_ai.providers` 抽象，不在这里写死 Ollama/FastAPI 请求细节。
- 这个文件会写数据库；如果只是纯模型/向量逻辑，应放在 `post_ai`。
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator

from django.conf import settings
from django.db import transaction

from apps.core.models import Citation, Conversation, Message, Ticket
from post_ai.config import AppConfig
from post_ai.pipeline import query_configured_vector_store
from post_ai.prompts import build_rag_messages, build_title_messages
from post_ai.providers import ProviderError, ProviderUnavailableError, build_default_registry
from post_ai.schemas import ChatMessage
from post_ai.tickets import TicketJSONError, build_rule_based_ticket, generate_ticket_json_with_provider
from post_ai.vectorstores import VectorStoreError


DIRECT_RAG_TOP_K = 0
LIGHT_RAG_TOP_K = 3
STRONG_RAG_TOP_K = 6
RAG_ROUTE_DIRECT = "DIRECT"
RAG_ROUTE_LIGHT = "LIGHT_RAG"
RAG_ROUTE_STRONG = "STRONG_RAG"
RAG_ROUTE_TO_PROFILE = {
    RAG_ROUTE_DIRECT: ("direct", DIRECT_RAG_TOP_K),
    RAG_ROUTE_LIGHT: ("light", LIGHT_RAG_TOP_K),
    RAG_ROUTE_STRONG: ("strong", STRONG_RAG_TOP_K),
}
DIRECT_RAG_PATTERNS = (
    "你好",
    "您好",
    "谢谢",
    "感谢",
    "再见",
    "拜拜",
    "你是谁",
    "现在几点",
    "几点了",
    "今天几号",
    "今天日期",
    "改写",
    "润色",
    "总结",
)
STRONG_RAG_KEYWORDS = (
    "清关",
    "报关",
    "海关",
    "赔付",
    "赔偿",
    "理赔",
    "投诉",
    "申诉",
    "改单",
    "禁寄",
    "限寄",
    "限制品",
    "危险品",
    "资费",
    "费用",
    "时限",
    "时效",
    "超时",
    "延误",
    "材料",
    "证明",
    "依据",
    "条款",
    "规则",
    "官方",
    "能不能寄",
    "是否可以",
    "需要准备",
    "多久能",
)


def create_conversation(title: str = "") -> Conversation:
    """创建一个新的会话记录。

    参数:
        title: 可选标题；为空时前端会显示“未命名会话”，后续也可能由模型或首条问题补齐。

    返回:
        已写入数据库的 `Conversation` 实例。
    """
    return Conversation.objects.create(title=title)


def get_or_create_conversation(conversation_id: int | None) -> Conversation:
    """按 id 获取会话；没有 id 时创建新会话。

    这是聊天入口的统一会话解析点，保证新会话和继续旧会话走同一套后续流程。
    """
    if conversation_id:
        return Conversation.objects.get(pk=conversation_id)
    return create_conversation()


def stream_chat_events(
    conversation_id: int | None,
    message: str,
    use_rag: bool,
    use_sft: bool,
) -> Iterator[dict]:
    """处理一次普通聊天请求，并以内部事件 dict 的形式流式返回。

    这里返回的是业务事件，不是 SSE 文本；路由层会用 `encode_sse` 做最后编码。
    副作用包括：保存用户消息、保存助手消息、保存引用和可能的错误消息。
    """
    conversation = get_or_create_conversation(conversation_id)
    Message.objects.create(conversation=conversation, role=Message.ROLE_USER, content=message)
    yield from _stream_reply_for_message(conversation, message, use_rag, use_sft)


def stream_retry_last_user_message_events(
    conversation: Conversation,
    message_id: int,
    message: str,
    use_rag: bool,
    use_sft: bool,
) -> Iterator[dict]:
    """重新回答或修改最后一条用户消息。

    只允许操作“最后一条用户消息”，避免用户改中间轮次导致后续上下文和工单引用不一致。
    删除逻辑放在事务中，确保用户消息更新、后续消息删除、旧工单清理要么一起成功，要么一起回滚。
    """
    with transaction.atomic():
        last_user = _last_user_message(conversation)
        if last_user is None:
            yield {"event": "error", "data": {"message": "没有可修改的上一条用户消息"}}
            return
        if last_user.id != message_id:
            yield {"event": "error", "data": {"message": "只能修改或重新回答上一条用户消息"}}
            return
        trailing_messages = conversation.messages.filter(
            created_at__gt=last_user.created_at,
        ) | conversation.messages.filter(
            created_at=last_user.created_at,
            id__gt=last_user.id,
        )
        # 重新回答时，最后一条用户消息之后的助手消息、错误消息和中间产物都不再可信。
        trailing_messages.delete()
        Ticket.objects.filter(conversation=conversation).delete()
        last_user.content = message
        last_user.save(update_fields=["content"])

    yield from _stream_reply_for_message(conversation, message, use_rag, use_sft)


def _stream_reply_for_message(
    conversation: Conversation,
    message: str,
    use_rag: bool,
    use_sft: bool,
) -> Iterator[dict]:
    """执行一轮完整回答流程。

    四种组合必须同时成立：
    - RAG 关 + SFT 关：默认模型直接回答。
    - RAG 开 + SFT 关：检索后交给默认模型回答。
    - RAG 关 + SFT 开：直接交给 SFT/LoRA 模型回答。
    - RAG 开 + SFT 开：检索后交给 SFT/LoRA 模型回答。

    这里会先产出 meta，再按需产出 citation，然后持续产出 delta，最后产出 done。
    """
    rag_profile, rag_top_k = _select_rag_profile(message, conversation) if use_rag else ("none", 0)

    yield {
        "event": "meta",
        "data": {
            "conversation_id": conversation.id,
            "use_rag": use_rag,
            "use_sft": use_sft,
            "rag_profile": rag_profile,
            "rag_top_k": rag_top_k,
        },
    }

    hits = []
    if use_rag and rag_top_k > 0:
        try:
            # 这里对应《邮政客服 LLM 系统设计报告》的核心 RAG 条数设计：
            # - Light RAG：常规业务问题只取 3 条，减少无效上下文和 token 成本。
            # - Strong RAG：规则、赔付、禁限寄、清关等高风险问题扩大到 6 条，优先保证依据充分。
            # 这一步仍然发生在同一轮回答中，不引入“先答一版、评分、再重答”的重链路。
            hits = query_configured_vector_store(message, top_k=rag_top_k)
        except (ProviderError, VectorStoreError, ValueError) as exc:
            error_message = f"RAG 检索失败：{exc}"
            _record_conversation_error(conversation, error_message)
            yield {
                "event": "error",
                "data": {
                    "message": error_message,
                },
            }
            return
        for hit in hits:
            # citation 先于模型 delta 返回，这样前端可以在回答过程中逐步展示检索来源。
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
        # 生成模型选择只由 use_sft 决定；prompt 是否带检索上下文只由 use_rag 决定。
        for content in _stream_assistant_answer(rag_messages, use_sft=use_sft):
            answer += content
            if content:
                yield {"event": "delta", "data": {"content": content}}
    except ProviderUnavailableError as exc:
        error_message = str(exc)
        _record_conversation_error(conversation, error_message)
        yield {"event": "error", "data": {"message": error_message}}
        return
    except ProviderError as exc:
        error_message = f"模型生成失败：{exc}"
        _record_conversation_error(conversation, error_message)
        yield {"event": "error", "data": {"message": error_message}}
        return

    assistant = Message.objects.create(
        conversation=conversation,
        role=Message.ROLE_ASSISTANT,
        content=answer,
        metadata={
            "rag_prompt": [item.model_dump() for item in rag_messages],
            "rag_profile": rag_profile,
            "rag_top_k": rag_top_k,
            "use_sft": use_sft,
            **_model_metadata(use_sft),
        },
    )

    for hit in hits:
        # 引用持久化绑定到助手消息，便于用户之后打开历史会话时重新看到来源。
        Citation.objects.create(
            message=assistant,
            score=hit.score,
            quoted_text=normalize_display_text(hit.document.content[:1000]),
            metadata=hit.document.metadata,
        )

    if use_sft and not conversation.title:
        # SFT 服务可能只启动了 FastAPI LoRA，没有默认标题模型；这里用用户问题兜底，避免额外依赖 Ollama。
        conversation.title = message[:20] or "未命名会话"
        conversation.save(update_fields=["title", "updated_at"])
    else:
        _ensure_conversation_title(conversation, message, answer)

    yield {"event": "done", "data": {"conversation_id": conversation.id, "message_id": assistant.id}}


def _last_user_message(conversation: Conversation) -> Message | None:
    """返回会话中最后一条用户消息，用于“修改/重新回答上一条”。"""
    return (
        conversation.messages.filter(role=Message.ROLE_USER)
        .order_by("-created_at", "-id")
        .first()
    )


def _select_rag_profile(message: str, conversation: Conversation | None = None) -> tuple[str, int]:
    """选择当前问题的 RAG 强度和召回条数。

    正式链路以 LLM Router 为主，Router 只允许输出 `DIRECT`、`LIGHT_RAG` 或
    `STRONG_RAG`。解析失败、模型不可用或输出异常时，统一按 Strong RAG 处理，避免
    把规则型问题误判成直接回答。关键词规则只作为 fake 测试模式和异常兜底里的保护栏。
    """
    if settings.POST_SERVICE_FAKE_LLM:
        route = _fallback_rag_route(message)
    else:
        try:
            route = _route_rag_with_llm(message, conversation)
        except ProviderError:
            route = RAG_ROUTE_STRONG
    return _route_to_rag_profile(route)


def _route_rag_with_llm(message: str, conversation: Conversation | None = None) -> str:
    """调用默认 chat provider 做轻量 RAG 路由。

    Router 只做分类，不生成最终回答。为了控制 token 和解析复杂度，要求模型只输出一个
    枚举词；如果模型没有严格遵守，后续 `_route_to_rag_profile` 会按 Strong RAG 兜底。
    """
    app_config = AppConfig.from_env()
    provider_settings = app_config.provider_settings
    provider = build_default_registry(provider_settings).get(provider_settings.default_chat_provider)
    result = provider.chat(
        messages=_build_rag_router_messages(message, conversation),
        model=provider_settings.default_chat_model,
        options={"temperature": 0},
    )
    return result.content.strip().upper()


def _build_rag_router_messages(
    message: str,
    conversation: Conversation | None = None,
) -> list[ChatMessage]:
    """构造 LLM Router 的极简 prompt，并带上最近多轮上下文。"""
    recent_context = _recent_router_context(conversation)
    user_content = "\n".join(
        [
            "最近对话:",
            recent_context or "无",
            "",
            "当前用户问题:",
            message,
            "",
            "只输出 DIRECT、LIGHT_RAG 或 STRONG_RAG 之一。",
        ]
    )
    return [
        ChatMessage(
            role="system",
            content=(
                "你是邮政客服系统的 RAG 路由器。你只判断当前用户问题是否需要检索知识库。\n"
                "你只能输出下面三个单词之一：DIRECT、LIGHT_RAG、STRONG_RAG。\n"
                "不要解释，不要输出 JSON，不要输出标点，不要输出其他文字。\n"
                "如果只是寒暄、感谢、结束语、闲聊、改写、润色、总结、格式调整，输出 DIRECT。\n"
                "如果只是问当前时间或当前日期，输出 DIRECT。\n"
                "如果是普通邮政 FAQ、业务流程咨询、常见寄递问题，输出 LIGHT_RAG。\n"
                "如果涉及清关、报关、海关、赔付、赔偿、理赔、投诉、申诉、改单、禁寄、限寄、"
                "危险品、资费、时限、时效、超时、延误、材料、证明、官方依据、条款、规则，"
                "输出 STRONG_RAG。\n"
                "多轮对话中，如果当前问题依赖上一轮业务上下文，按业务问题处理，不要因为当前"
                "句子短就输出 DIRECT。\n"
                "如果不确定，输出 STRONG_RAG。"
            ),
        ),
        ChatMessage(role="user", content=user_content),
    ]


def _recent_router_context(conversation: Conversation | None, limit: int = 6) -> str:
    """取最近几轮消息给 Router 判断多轮追问语境。"""
    if conversation is None:
        return ""
    messages = list(conversation.messages.order_by("-created_at", "-id")[:limit])
    messages.reverse()
    lines = []
    for item in messages:
        if item.role == Message.ROLE_SYSTEM:
            continue
        content = normalize_display_text(item.content)[:300]
        lines.append(f"{item.role}: {content}")
    return "\n".join(lines)


def _route_to_rag_profile(route: str) -> tuple[str, int]:
    """把 Router 输出映射成内部 profile；无法解析时按 Strong RAG。"""
    normalized = route.strip().upper()
    return RAG_ROUTE_TO_PROFILE.get(normalized, RAG_ROUTE_TO_PROFILE[RAG_ROUTE_STRONG])


def _fallback_rag_route(message: str) -> str:
    """Router 不可用时的保守兜底，仅用于测试和异常保护。"""
    normalized = message.strip().lower()
    if any(pattern.lower() in normalized for pattern in DIRECT_RAG_PATTERNS):
        return RAG_ROUTE_DIRECT
    if any(keyword.lower() in normalized for keyword in STRONG_RAG_KEYWORDS):
        return RAG_ROUTE_STRONG
    return RAG_ROUTE_LIGHT


def encode_sse(event: dict) -> str:
    """把内部事件 dict 编码成浏览器 EventSource/Fetch 可消费的 SSE 文本。"""
    return f"event: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"


def _first_issue_type(hits) -> str:
    """从检索结果中取第一个 intent，作为规则工单 issue_type 的弱信号。"""
    for hit in hits:
        intents = hit.document.metadata.get("intents") or []
        if intents:
            return intents[0]
    return ""


def normalize_display_text(text: str) -> str:
    """清理检索文本中的异常空格和对话边界，避免前端引用展示难读。

    主要处理中文字符之间的多余空格、标点前后的空格、以及“用户[n]/客服[n]”连在一起的问题。
    """
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    text = re.sub(r"\s+([，。！？；：、“”）])", r"\1", text)
    text = re.sub(r"([，。！？；：、“”])\s+(?=[\u4e00-\u9fff])", r"\1", text)
    text = re.sub(r"([（“])\s+", r"\1", text)
    text = re.sub(r"(?<!^)(?=(?:用户|客服)\[\d+\]:)", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text


def _stream_assistant_answer(messages, use_sft: bool = False) -> Iterator[str]:
    """按开关选择默认模型或 SFT 模型，并流式产出文本片段。

    注意：即使测试环境启用了 fake LLM，也必须先解析 SFT 配置。
    这样可以确保“勾选 SFT 但未配置模型”仍然返回明确错误，而不是被 fake 回答掩盖。
    """
    app_config = AppConfig.from_env()
    provider_settings = app_config.provider_settings
    provider_name, model = _select_generation_model(provider_settings, use_sft)

    if settings.POST_SERVICE_FAKE_LLM:
        yield "已收到问题。当前已接入 Django 和 post_ai。"
        return

    registry = build_default_registry(provider_settings)
    provider = registry.get(provider_name)
    for delta in provider.stream_chat(
        messages=messages,
        model=model,
    ):
        if delta.content:
            yield delta.content


def _select_generation_model(provider_settings, use_sft: bool) -> tuple[str, str]:
    """根据 SFT 开关选择 provider/model。

    返回:
        `(provider_name, model_name)`，供 registry 查找 provider 并发起模型调用。

    异常:
        `ProviderUnavailableError`：用户勾选 SFT，但配置里没有 SFT provider 或 model。
    """
    if not use_sft:
        return provider_settings.default_chat_provider, provider_settings.default_chat_model
    if not provider_settings.sft_provider or not provider_settings.sft_model:
        error_message = "当前不存在 SFT 模型"
        raise ProviderUnavailableError(error_message)
    return provider_settings.sft_provider, provider_settings.sft_model


def _model_metadata(use_sft: bool) -> dict:
    """生成要写入助手消息 metadata 的模型来源信息。"""
    app_config = AppConfig.from_env()
    provider_settings = app_config.provider_settings
    try:
        provider_name, model = _select_generation_model(provider_settings, use_sft)
    except ProviderUnavailableError:
        provider_name, model = "", ""
    return {"provider": provider_name, "model": model}


def _ensure_conversation_title(conversation: Conversation, user_message: str, answer: str) -> None:
    """确保会话有标题。

    普通模型路径会尝试让默认 chat provider 根据首轮问答生成标题。
    fake LLM 或标题模型不可用场景下，使用用户问题前 20 个字符兜底。
    """
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


def _record_conversation_error(conversation: Conversation, message: str) -> None:
    """把一次业务错误写入系统消息，并在无标题会话中用错误摘要作为标题。"""
    Message.objects.create(
        conversation=conversation,
        role=Message.ROLE_SYSTEM,
        content=message,
        metadata={"kind": "error"},
    )
    if not conversation.title:
        conversation.title = message[:128]
        conversation.save(update_fields=["title", "updated_at"])


def generate_ticket_for_conversation(conversation: Conversation) -> Ticket:
    """为会话生成或返回已有工单。

    工单只生成一次：如果会话已经有工单，直接返回旧工单，避免用户多次点击造成内容漂移。
    优先尝试模型生成 JSON；失败时用规则层兜底，保证 UI 始终有可展示的工单对象。
    """
    existing = conversation.tickets.order_by("created_at", "id").first()
    if existing:
        return existing

    messages = list(conversation.messages.order_by("created_at", "id"))
    user_messages = [message.content for message in messages if message.role == Message.ROLE_USER]
    assistant_messages = [
        message.content for message in messages if message.role == Message.ROLE_ASSISTANT
    ]
    conversation_text = _ticket_conversation_text(messages)
    ticket = None
    if not settings.POST_SERVICE_FAKE_LLM:
        try:
            app_config = AppConfig.from_env()
            provider_settings = app_config.provider_settings
            provider = build_default_registry(provider_settings).get(provider_settings.default_chat_provider)
            ticket = generate_ticket_json_with_provider(
                provider=provider,
                model=provider_settings.default_chat_model,
                conversation_text=conversation_text,
            )
        except (ProviderError, TicketJSONError, ValueError):
            ticket = None
    if ticket is None:
        ticket = build_rule_based_ticket(
            user_request=_compact_text("\n".join(user_messages).strip(), 120),
            summary=_compact_text(assistant_messages[-1] if assistant_messages else "", 180),
            issue_type=_latest_issue_type(conversation),
            need_follow_up=False,
        )
    ticket.user_id = f"conversation:{conversation.id}"
    return Ticket.objects.create(
        conversation=conversation,
        message=messages[-1] if messages else None,
        payload=ticket.model_dump(),
        is_valid=True,
    )


def provider_health_payload() -> dict:
    """返回前端顶部健康状态条需要展示的 provider 摘要。

    这里只返回配置状态，不主动探测外部服务是否真的在线。
    例如 `sft_configured=True` 表示已配置 SFT provider/model；
    但 FastAPI LoRA 服务是否正在监听端口，需要实际发送聊天请求才能最终确认。
    """
    config = AppConfig.from_env()
    provider_settings = config.provider_settings
    return {
        "chat_provider": provider_settings.default_chat_provider,
        "chat_model": provider_settings.default_chat_model,
        "embedding_provider": provider_settings.default_embedding_provider,
        "embedding_model": provider_settings.default_embedding_model,
        "vector_provider": config.vector_store_settings.provider,
        "sft_configured": bool(provider_settings.sft_provider and provider_settings.sft_model),
    }


def _latest_issue_type(conversation: Conversation) -> str:
    """从最近一次引用 metadata 中提取 intent，作为规则工单的分类依据。

    这个分类不是强事实，只是 RAG 数据中已有标签的继承；没有引用或没有 intents 时返回空字符串。
    """
    citation = (
        Citation.objects.filter(message__conversation=conversation)
        .order_by("-created_at", "-id")
        .first()
    )
    if not citation:
        return ""
    intents = citation.metadata.get("intents") or []
    return intents[0] if intents else ""


def _ticket_conversation_text(messages: list[Message]) -> str:
    """把会话消息压成模型生成工单时使用的纯文本上下文。

    系统错误消息不参与工单生成，避免把“模型失败”“RAG 失败”等运行错误误写成用户诉求。
    """
    lines = []
    for message in messages:
        if message.role == Message.ROLE_SYSTEM:
            continue
        role = "用户" if message.role == Message.ROLE_USER else "助手"
        lines.append(f"{role}: {message.content}")
    return "\n".join(lines)


def _compact_text(text: str, limit: int) -> str:
    """压缩文本并截断到指定长度，用于规则工单兜底字段。"""
    text = normalize_display_text(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]
