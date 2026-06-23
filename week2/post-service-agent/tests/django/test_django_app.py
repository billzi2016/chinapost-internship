from __future__ import annotations

import json
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.core.models import Citation, Conversation, Message, PostalDocument, Ticket
from apps.api.services import normalize_display_text
from post_ai.config import AppConfig


@override_settings(POST_SERVICE_FAKE_LLM=True)
class DjangoSmokeTests(TestCase):
    def test_settings_load_post_ai_yaml(self) -> None:
        config = AppConfig.from_env()

        self.assertEqual(config.provider_settings.default_chat_provider, "ollama")
        self.assertEqual(config.mode, "microservice")
        self.assertEqual(config.vector_store_settings.provider, "pgvector")

    def test_chat_page_renders_light_template(self) -> None:
        response = Client().get(reverse("chat"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "邮政智能助手")
        self.assertContains(response, "检索增强生成（RAG）")
        self.assertContains(response, "监督微调模型（SFT）")

    def test_chat_page_escapes_conversation_title(self) -> None:
        Conversation.objects.create(title="<script>alert(1)</script>")

        response = Client().get(reverse("chat"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<script>alert(1)</script>", html=False)
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;", html=False)

    def test_state_changing_api_requires_csrf(self) -> None:
        client = Client(enforce_csrf_checks=True)

        response = client.post(
            "/api/conversations",
            data=json.dumps({"title": "csrf"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)

    def test_state_changing_api_accepts_valid_csrf(self) -> None:
        client = Client(enforce_csrf_checks=True)
        client.get(reverse("chat"))
        token = client.cookies["csrftoken"].value

        response = client.post(
            "/api/conversations",
            data=json.dumps({"title": "csrf"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 200)

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
        conversation = Conversation.objects.get()
        self.assertEqual(conversation.title, "当前不存在 SFT 模型")
        self.assertEqual(conversation.latest_error, "当前不存在 SFT 模型")

        listed = Client().get("/api/conversations").json()
        self.assertEqual(listed[0]["title"], "当前不存在 SFT 模型")
        self.assertEqual(listed[0]["latest_error"], "当前不存在 SFT 模型")

    def test_error_keeps_existing_title_and_adds_error_summary(self) -> None:
        conversation = Conversation.objects.create(title="已有会话")

        response = Client().post(
            "/api/chat/stream",
            data=json.dumps(
                {
                    "conversation_id": conversation.id,
                    "message": "测试",
                    "use_rag": False,
                    "use_sft": True,
                }
            ),
            content_type="application/json",
        )

        body = b"".join(response.streaming_content).decode("utf-8")
        conversation.refresh_from_db()
        self.assertIn("当前不存在 SFT 模型", body)
        self.assertEqual(conversation.title, "已有会话")
        self.assertEqual(conversation.latest_error, "当前不存在 SFT 模型")

    def test_non_sft_stream_saves_messages_without_auto_ticket(self) -> None:
        response = Client().post(
            "/api/chat/stream",
            data=json.dumps({"message": "包裹什么时候派送", "use_rag": False, "use_sft": False}),
            content_type="application/json",
        )

        body = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("event: meta", body)
        self.assertIn("event: delta", body)
        self.assertNotIn("event: ticket", body)
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 2)
        self.assertEqual(Ticket.objects.count(), 0)
        self.assertEqual(Conversation.objects.first().title, "包裹什么时候派送")

    def test_ticket_is_generated_manually_for_conversation(self) -> None:
        conversation = Conversation.objects.create(title="测试")
        Message.objects.create(
            conversation=conversation,
            role=Message.ROLE_USER,
            content="包裹什么时候派送",
        )
        Message.objects.create(
            conversation=conversation,
            role=Message.ROLE_ASSISTANT,
            content="请等待配送通知。",
        )

        generated = Client().post(f"/api/conversations/{conversation.id}/ticket/generate")
        latest = Client().get(f"/api/conversations/{conversation.id}/ticket")

        self.assertEqual(generated.status_code, 200)
        self.assertEqual(latest.status_code, 200)
        self.assertEqual(Ticket.objects.count(), 1)
        self.assertEqual(generated.json()["payload"]["user_request"], "包裹什么时候派送")

    def test_ticket_generation_is_idempotent_after_first_ticket(self) -> None:
        conversation = Conversation.objects.create(title="测试")
        Message.objects.create(
            conversation=conversation,
            role=Message.ROLE_USER,
            content="第一次问题",
        )
        Message.objects.create(
            conversation=conversation,
            role=Message.ROLE_ASSISTANT,
            content="第一次回答",
        )
        client = Client()

        first = client.post(f"/api/conversations/{conversation.id}/ticket/generate")
        Message.objects.create(
            conversation=conversation,
            role=Message.ROLE_USER,
            content="第二次问题",
        )
        second = client.post(f"/api/conversations/{conversation.id}/ticket/generate")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(Ticket.objects.count(), 1)
        self.assertEqual(first.json()["id"], second.json()["id"])
        self.assertEqual(second.json()["payload"]["user_request"], "第一次问题")

    def test_provider_health_api(self) -> None:
        response = Client().get("/api/provider/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["chat_provider"], "ollama")
        self.assertEqual(response.json()["vector_provider"], "pgvector")

    def test_provider_health_respects_vector_provider_override(self) -> None:
        import os

        old_provider = os.environ.get("POST_AI_VECTOR_PROVIDER")
        os.environ["POST_AI_VECTOR_PROVIDER"] = "faiss"
        self.addCleanup(
            lambda: (
                os.environ.pop("POST_AI_VECTOR_PROVIDER", None)
                if old_provider is None
                else os.environ.__setitem__("POST_AI_VECTOR_PROVIDER", old_provider)
            )
        )

        response = Client().get("/api/provider/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["vector_provider"], "faiss")

    @override_settings(POST_SERVICE_FAKE_LLM=True)
    def test_rag_stream_returns_citations_when_faiss_is_available(self) -> None:
        import os

        old_provider = os.environ.get("POST_AI_VECTOR_PROVIDER")
        os.environ["POST_AI_VECTOR_PROVIDER"] = "faiss"
        self.addCleanup(
            lambda: (
                os.environ.pop("POST_AI_VECTOR_PROVIDER", None)
                if old_provider is None
                else os.environ.__setitem__("POST_AI_VECTOR_PROVIDER", old_provider)
            )
        )

        response = Client().post(
            "/api/chat/stream",
            data=json.dumps({"message": "包裹什么时候派送", "use_rag": True, "use_sft": False}),
            content_type="application/json",
        )

        body = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("event: meta", body)
        self.assertIn("event: citation", body)
        self.assertIn("event: delta", body)
        self.assertIn("event: done", body)

    def test_message_api_returns_saved_citations(self) -> None:
        conversation = Conversation.objects.create(title="测试")
        assistant = Message.objects.create(
            conversation=conversation,
            role=Message.ROLE_ASSISTANT,
            content="回答",
        )
        Citation.objects.create(
            message=assistant,
            score=0.82,
            quoted_text="用户[0]: 你好\n客服[1]: 您好",
            metadata={"intents": ["配送周期"]},
        )

        response = Client().get(f"/api/conversations/{conversation.id}/messages")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["citations"][0]["score"], 0.82)
        self.assertIn("用户[0]:", response.json()[0]["citations"][0]["quoted_text"])

    def test_ingest_postal_rag_is_idempotent_with_limit(self) -> None:
        output = StringIO()
        call_command("ingest_postal_rag", "--limit", "2", stdout=output)
        call_command("ingest_postal_rag", "--limit", "2", stdout=output)

        self.assertEqual(PostalDocument.objects.count(), 2)
        self.assertIn("documents_created=2", output.getvalue())
        self.assertIn("documents_updated=2", output.getvalue())

    def test_normalize_display_text_removes_chinese_spacing(self) -> None:
        text = "用户 询问 邮寄 的 信息 ， 客服 回复 。"

        self.assertEqual(normalize_display_text(text), "用户询问邮寄的信息，客服回复。")

    def test_normalize_display_text_splits_dialogue_turns(self) -> None:
        text = "用户[0]: 你好客服[1]: 您好用户[2]: 查询一下"

        self.assertEqual(
            normalize_display_text(text),
            "用户[0]: 你好\n客服[1]: 您好\n用户[2]: 查询一下",
        )
