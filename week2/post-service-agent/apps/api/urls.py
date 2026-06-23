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
    TicketOut,
)
from apps.api.services import (
    create_conversation,
    encode_sse,
    generate_ticket_for_conversation,
    provider_health_payload,
    stream_chat_events,
)
from apps.core.models import Conversation, Message


api = NinjaAPI(title="Post Service Agent API")


def csrf_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        reason = CsrfViewMiddleware(lambda _request: None).process_view(request, None, (), {})
        if reason is not None:
            return HttpResponseForbidden("CSRF verification failed.")
        return view_func(request, *args, **kwargs)

    return wrapped


@api.get("/conversations", response=list[ConversationOut])
def list_conversations(request):
    return list(Conversation.objects.all())


@api.post("/conversations", response=ConversationOut)
@csrf_required
def create_conversation_api(request, payload: ConversationCreateIn):
    return create_conversation(payload.title)


@api.get("/conversations/{conversation_id}/messages", response=list[MessageOut])
def list_messages(request, conversation_id: int):
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
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    conversation.is_pinned = not conversation.is_pinned
    conversation.save(update_fields=["is_pinned", "updated_at"])
    return conversation


@api.delete("/conversations/{conversation_id}")
@csrf_required
def delete_conversation(request, conversation_id: int):
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    conversation.delete()
    return {"ok": True}


@api.post("/conversations/{conversation_id}/messages", response=MessageOut)
@csrf_required
def create_message(request, conversation_id: int, payload: MessageCreateIn):
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    return Message.objects.create(
        conversation=conversation,
        role=Message.ROLE_USER,
        content=payload.content,
    )


@api.post("/chat/stream")
@csrf_required
def chat_stream(request, payload: ChatPreviewIn):
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


@api.get("/provider/health", response=ProviderHealthOut)
def provider_health(request):
    return provider_health_payload()


@api.get("/conversations/{conversation_id}/ticket", response=TicketOut | None)
def get_latest_ticket(request, conversation_id: int):
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    return conversation.tickets.order_by("created_at", "id").first()


@api.post("/conversations/{conversation_id}/ticket/generate", response=TicketOut)
@csrf_required
def generate_ticket(request, conversation_id: int):
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    return generate_ticket_for_conversation(conversation)
