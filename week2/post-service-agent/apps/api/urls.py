from __future__ import annotations

from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from ninja import NinjaAPI

from apps.api.schemas import (
    ChatPreviewIn,
    ConversationCreateIn,
    ConversationOut,
    MessageCreateIn,
    MessageOut,
)
from apps.api.services import create_conversation, encode_sse, stream_chat_events
from apps.core.models import Conversation, Message


api = NinjaAPI(title="Post Service Agent API")


@api.get("/conversations", response=list[ConversationOut])
def list_conversations(request):
    return list(Conversation.objects.all())


@api.post("/conversations", response=ConversationOut)
def create_conversation_api(request, payload: ConversationCreateIn):
    return create_conversation(payload.title)


@api.get("/conversations/{conversation_id}/messages", response=list[MessageOut])
def list_messages(request, conversation_id: int):
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    return list(conversation.messages.all())


@api.patch("/conversations/{conversation_id}/pin", response=ConversationOut)
def toggle_pin_conversation(request, conversation_id: int):
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    conversation.is_pinned = not conversation.is_pinned
    conversation.save(update_fields=["is_pinned", "updated_at"])
    return conversation


@api.delete("/conversations/{conversation_id}")
def delete_conversation(request, conversation_id: int):
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    conversation.delete()
    return {"ok": True}


@api.post("/conversations/{conversation_id}/messages", response=MessageOut)
def create_message(request, conversation_id: int, payload: MessageCreateIn):
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    return Message.objects.create(
        conversation=conversation,
        role=Message.ROLE_USER,
        content=payload.content,
    )


@api.post("/chat/stream")
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
