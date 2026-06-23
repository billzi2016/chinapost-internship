from __future__ import annotations

import json
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.core.models import Conversation, Message, PostalDocument, Ticket
from apps.api.services import normalize_display_text
from post_ai.config import AppConfig


@override_settings(POST_SERVICE_FAKE_LLM=True)
class DjangoSmokeTests(TestCase):
    def test_settings_load_post_ai_yaml(self) -> None:
        config = AppConfig.from_env()

        self.assertEqual(config.provider_settings.default_chat_provider, "ollama")
        self.assertEqual(config.vector_store_settings.provider, "faiss")

    def test_chat_page_renders_light_template(self) -> None:
        response = Client().get(reverse("chat"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "邮政智能助手")
        self.assertContains(response, "检索增强生成（RAG）")
        self.assertContains(response, "监督微调模型（SFT）")

    def test_conversation_api_create_and_list(self) -> None:
        client = Client()
        created = client.post(
            "/api/conversations",
            data=json.dumps({"title": "测试会话"}),
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 200)

        listed = client.get("/api/conversations")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()[0]["title"], "测试会话")

    def test_conversation_pin_and_delete_api(self) -> None:
        conversation = Conversation.objects.create(title="测试")
        client = Client()

        pinned = client.patch(f"/api/conversations/{conversation.id}/pin")
        self.assertEqual(pinned.status_code, 200)
        self.assertTrue(pinned.json()["is_pinned"])

        deleted = client.delete(f"/api/conversations/{conversation.id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(Conversation.objects.count(), 0)

    def test_sft_stream_returns_error_without_creating_assistant_message(self) -> None:
        response = Client().post(
            "/api/chat/stream",
            data=json.dumps({"message": "测试", "use_rag": False, "use_sft": True}),
            content_type="application/json",
        )

        body = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("event: meta", body)
        self.assertIn("event: error", body)
        self.assertIn("当前不存在 SFT 模型", body)
        self.assertEqual(Message.objects.filter(role=Message.ROLE_ASSISTANT).count(), 0)

    def test_non_sft_stream_saves_messages_and_ticket(self) -> None:
        response = Client().post(
            "/api/chat/stream",
            data=json.dumps({"message": "包裹什么时候派送", "use_rag": False, "use_sft": False}),
            content_type="application/json",
        )

        body = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("event: meta", body)
        self.assertIn("event: delta", body)
        self.assertIn("event: ticket", body)
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 2)
        self.assertEqual(Ticket.objects.count(), 1)
        self.assertEqual(Conversation.objects.first().title, "包裹什么时候派送")

    def test_rag_stream_returns_clear_error_when_provider_unavailable(self) -> None:
        response = Client().post(
            "/api/chat/stream",
            data=json.dumps({"message": "包裹什么时候派送", "use_rag": True, "use_sft": False}),
            content_type="application/json",
        )

        body = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("event: meta", body)
        self.assertIn("event: error", body)
        self.assertIn("RAG 检索失败", body)

    def test_ingest_postal_rag_is_idempotent_with_limit(self) -> None:
        output = StringIO()
        call_command("ingest_postal_rag", "--limit", "2", stdout=output)
        call_command("ingest_postal_rag", "--limit", "2", stdout=output)

        self.assertEqual(PostalDocument.objects.count(), 2)
        self.assertIn("created=2", output.getvalue())
        self.assertIn("updated=2", output.getvalue())

    def test_normalize_display_text_removes_chinese_spacing(self) -> None:
        text = "用户 询问 邮寄 的 信息 ， 客服 回复 。"

        self.assertEqual(normalize_display_text(text), "用户询问邮寄的信息，客服回复。")
