"""Django Ninja API 路由层。

这个文件只负责 HTTP 边界：
- 定义 URL、请求 schema、响应 schema；
- 处理 CSRF、404、StreamingHttpResponse 等 Web 框架细节；
- 调用 `apps.api.services` 完成真正业务逻辑。

维护约定：
- 不在路由函数里写模型调用、RAG 检索或复杂数据库编排。
- 修改会话/消息/工单等状态的接口必须挂 `@csrf_required`。
- SSE 接口只把 service 层事件编码成文本流，不改变事件语义。
"""

from __future__ import annotations

from functools import wraps

from django.middleware.csrf import CsrfViewMiddleware
from django.http import HttpResponseForbidden
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from ninja import NinjaAPI

from apps.api.schemas import (
    ChatPreviewIn,
    ConversationCreateIn,
    ConversationOut,
    MessageCreateIn,
    MessageOut,
    ProviderHealthOut,
    RetryLastMessageIn,
    TicketOut,
)
from apps.api.services import (
    create_conversation,
    encode_sse,
    generate_ticket_for_conversation,
    provider_health_payload,
    stream_retry_last_user_message_events,
    stream_chat_events,
)
from apps.core.models import Conversation, Message


api = NinjaAPI(title="Post Service Agent API")


def csrf_required(view_func):
    """为 django-ninja 路由补上 Django 原生 CSRF 校验。

    Ninja 默认更偏 API 使用场景；本项目的前端页面和 API 同源运行，
    因此会话创建、删除、发送消息等会改变状态的接口都应该复用 Django 的 CSRF 保护。
    """
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        # `process_view` 返回 None 表示校验通过；返回响应对象表示失败原因。
        reason = CsrfViewMiddleware(lambda _request: None).process_view(request, None, (), {})
        if reason is not None:
            return HttpResponseForbidden("CSRF verification failed.")
        return view_func(request, *args, **kwargs)

    return wrapped


@api.get("/conversations", response=list[ConversationOut])
def list_conversations(request):
    """列出侧边栏会话。

    排序规则由 `Conversation.Meta.ordering` 统一控制，路由层不重复写排序逻辑。
    """
    return list(Conversation.objects.all())


@api.post("/conversations", response=ConversationOut)
@csrf_required
def create_conversation_api(request, payload: ConversationCreateIn):
    """创建一个空会话，供“新建会话”按钮或 API 调用使用。"""
    return create_conversation(payload.title)


@api.get("/conversations/{conversation_id}/messages", response=list[MessageOut])
def list_messages(request, conversation_id: int):
    """读取某个会话的完整消息历史和引用。

    返回结构需要适配前端历史会话渲染：助手消息会带 citations，用户消息通常没有 citations。
    """
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    items = []
    for message in conversation.messages.prefetch_related("citations").all():
        items.append(
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "metadata": message.metadata,
                "created_at": message.created_at,
                "citations": [
                    {
                        "score": citation.score,
                        "quoted_text": citation.quoted_text,
                        "metadata": citation.metadata,
                    }
                    for citation in message.citations.all()
                ],
            }
        )
    return items


@api.patch("/conversations/{conversation_id}/pin", response=ConversationOut)
@csrf_required
def toggle_pin_conversation(request, conversation_id: int):
    """切换会话置顶状态。"""
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    conversation.is_pinned = not conversation.is_pinned
    conversation.save(update_fields=["is_pinned", "updated_at"])
    return conversation


@api.delete("/conversations/{conversation_id}")
@csrf_required
def delete_conversation(request, conversation_id: int):
    """删除一个会话及其级联消息、引用和工单。"""
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    conversation.delete()
    return {"ok": True}


@api.post("/conversations/{conversation_id}/messages", response=MessageOut)
@csrf_required
def create_message(request, conversation_id: int, payload: MessageCreateIn):
    """给指定会话追加一条用户消息。

    当前主要保留给 API 完整性；正常聊天入口走 `/chat/stream`，它会同时保存用户消息并生成回答。
    """
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    return Message.objects.create(
        conversation=conversation,
        role=Message.ROLE_USER,
        content=payload.content,
    )


@api.post("/chat/stream")
@csrf_required
def chat_stream(request, payload: ChatPreviewIn):
    """发起一次聊天并返回 SSE 流。

    这里不直接生成文本；`stream_chat_events` 会按 meta/citation/delta/done/error 产出内部事件。
    """
    response = StreamingHttpResponse(
        (encode_sse(event) for event in stream_chat_events(
            conversation_id=payload.conversation_id,
            message=payload.message,
            use_rag=payload.use_rag,
            use_sft=payload.use_sft,
        )),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    return response


@api.post("/conversations/{conversation_id}/last-user-message/retry")
@csrf_required
def retry_last_user_message(request, conversation_id: int, payload: RetryLastMessageIn):
    """基于最后一条用户消息重新生成回答，或先修改它再重新生成。

    service 层会保证只能处理最后一条用户消息，并清掉这条消息之后的旧回答和旧工单。
    """
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    response = StreamingHttpResponse(
        (encode_sse(event) for event in stream_retry_last_user_message_events(
            conversation=conversation,
            message_id=payload.message_id,
            message=payload.message,
            use_rag=payload.use_rag,
            use_sft=payload.use_sft,
        )),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    return response


@api.get("/provider/health", response=ProviderHealthOut)
def provider_health(request):
    """返回前端状态条需要展示的模型/向量/SFT 配置状态。"""
    return provider_health_payload()


@api.get("/conversations/{conversation_id}/ticket", response=TicketOut | None)
def get_latest_ticket(request, conversation_id: int):
    """读取会话当前工单；没有生成过时返回 null。"""
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    return conversation.tickets.order_by("created_at", "id").first()


@api.post("/conversations/{conversation_id}/ticket/generate", response=TicketOut)
@csrf_required
def generate_ticket(request, conversation_id: int):
    """为会话生成工单。

    生成逻辑具备幂等性：已有工单时 service 层会直接返回旧工单，避免重复生成导致结果漂移。
    """
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    return generate_ticket_for_conversation(conversation)
