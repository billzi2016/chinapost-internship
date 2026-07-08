"""Django Web/API 冒烟测试。

这些测试覆盖项目的外层行为：
- 页面能渲染；
- CSRF 保护生效；
- 会话、消息、重试、工单等核心 API 能工作；
- SFT 未配置时能清晰报错；
- 管理命令和文本清理逻辑保持稳定。

测试类默认开启 `POST_SERVICE_FAKE_LLM=True`，避免单元测试依赖真实 Ollama/FastAPI/LoRA 服务。
"""

from __future__ import annotations

import json
import os
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.core.models import Citation, Conversation, Message, PostalDocument, Ticket
from apps.api.services import normalize_display_text
from post_ai.config import AppConfig


@override_settings(POST_SERVICE_FAKE_LLM=True)
class DjangoSmokeTests(TestCase):
    """Django 层端到端冒烟测试。

    这里不验证模型质量，只验证 Django 编排、数据库副作用和前端可消费的响应格式。
    """

    def test_settings_load_post_ai_yaml(self) -> None:
        """确认 Django 测试环境能读取 post_ai.yaml 的关键配置。"""
        config = AppConfig.from_env()

        self.assertEqual(config.provider_settings.default_chat_provider, "ollama")
        self.assertEqual(config.mode, "microservice")
        self.assertEqual(config.vector_store_settings.provider, "pgvector")

    def test_chat_page_renders_light_template(self) -> None:
        """确认聊天页面可以渲染，并包含核心模式开关。"""
        response = Client().get(reverse("chat"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "邮政智能助手")
        self.assertContains(response, "检索增强生成（RAG）")
        self.assertContains(response, "监督微调模型（SFT）")

    def test_chat_page_escapes_conversation_title(self) -> None:
        """确认历史会话标题会被模板转义，避免脚本注入。"""
        Conversation.objects.create(title="<script>alert(1)</script>")

        response = Client().get(reverse("chat"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<script>alert(1)</script>", html=False)
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;", html=False)

    def test_state_changing_api_requires_csrf(self) -> None:
        """会改变状态的接口必须拒绝缺少 CSRF token 的请求。"""
        client = Client(enforce_csrf_checks=True)

        response = client.post(
            "/api/conversations",
            data=json.dumps({"title": "csrf"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)

    def test_state_changing_api_accepts_valid_csrf(self) -> None:
        """同源页面拿到合法 CSRF token 后，应允许状态变更请求。"""
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
        """创建会话后，列表接口应立即返回该会话。"""
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
        """置顶和删除接口应正确修改 Conversation 状态。"""
        conversation = Conversation.objects.create(title="测试")
        client = Client()

        pinned = client.patch(f"/api/conversations/{conversation.id}/pin")
        self.assertEqual(pinned.status_code, 200)
        self.assertTrue(pinned.json()["is_pinned"])

        deleted = client.delete(f"/api/conversations/{conversation.id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(Conversation.objects.count(), 0)

    def test_sft_stream_returns_error_without_configured_model(self) -> None:
        """SFT 未配置时，勾选 SFT 应返回明确错误且不创建助手消息。

        这里故意忽略 YAML，并清空 SFT 环境变量，模拟全局未配置 SFT 的部署状态。
        """
        os.environ["POST_AI_IGNORE_YAML"] = "1"
        os.environ.pop("SFT_PROVIDER", None)
        os.environ.pop("SFT_MODEL", None)
        os.environ.pop("SFT_FASTAPI_BASE_URL", None)
        self.addCleanup(os.environ.pop, "POST_AI_IGNORE_YAML", None)

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
        """已有标题的会话遇到错误时，标题不应被错误信息覆盖。"""
        os.environ["POST_AI_IGNORE_YAML"] = "1"
        os.environ.pop("SFT_PROVIDER", None)
        os.environ.pop("SFT_MODEL", None)
        os.environ.pop("SFT_FASTAPI_BASE_URL", None)
        self.addCleanup(os.environ.pop, "POST_AI_IGNORE_YAML", None)
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
        """普通聊天应保存用户和助手消息，但不会自动生成工单。"""
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

    def test_retry_last_user_message_replaces_only_last_turn(self) -> None:
        """重新回答最后一轮时，只清理最后一条用户消息之后的旧产物。"""
        conversation = Conversation.objects.create(title="测试")
        first_user = Message.objects.create(
            conversation=conversation,
            role=Message.ROLE_USER,
            content="第一条",
        )
        Message.objects.create(
            conversation=conversation,
            role=Message.ROLE_ASSISTANT,
            content="第一条回答",
        )
        last_user = Message.objects.create(
            conversation=conversation,
            role=Message.ROLE_USER,
            content="旧问题",
        )
        old_assistant = Message.objects.create(
            conversation=conversation,
            role=Message.ROLE_ASSISTANT,
            content="旧回答",
        )
        Citation.objects.create(
            message=old_assistant,
            score=0.8,
            quoted_text="用户[0]: 旧",
            metadata={},
        )
        Ticket.objects.create(
            conversation=conversation,
            message=old_assistant,
            payload={"user_request": "旧问题"},
            is_valid=True,
        )

        response = Client().post(
            f"/api/conversations/{conversation.id}/last-user-message/retry",
            data=json.dumps(
                {
                    "message_id": last_user.id,
                    "message": "新问题",
                    "use_rag": False,
                    "use_sft": False,
                }
            ),
            content_type="application/json",
        )

        body = b"".join(response.streaming_content).decode("utf-8")
        last_user.refresh_from_db()
        self.assertIn("event: done", body)
        self.assertEqual(first_user.content, "第一条")
        self.assertEqual(last_user.content, "新问题")
        self.assertFalse(Message.objects.filter(content="旧回答").exists())
        self.assertEqual(Citation.objects.count(), 0)
        self.assertEqual(Ticket.objects.count(), 0)
        self.assertEqual(Message.objects.filter(role=Message.ROLE_ASSISTANT).count(), 2)

    def test_retry_last_user_message_rejects_stale_message_id(self) -> None:
        """禁止修改非最后一条用户消息，避免中间轮次被改后上下文错乱。"""
        conversation = Conversation.objects.create(title="测试")
        first_user = Message.objects.create(
            conversation=conversation,
            role=Message.ROLE_USER,
            content="第一条",
        )
        first_assistant = Message.objects.create(
            conversation=conversation,
            role=Message.ROLE_ASSISTANT,
            content="第一条回答",
        )
        last_user = Message.objects.create(
            conversation=conversation,
            role=Message.ROLE_USER,
            content="最后一条",
        )
        last_assistant = Message.objects.create(
            conversation=conversation,
            role=Message.ROLE_ASSISTANT,
            content="最后回答",
        )

        response = Client().post(
            f"/api/conversations/{conversation.id}/last-user-message/retry",
            data=json.dumps(
                {
                    "message_id": first_user.id,
                    "message": "误改第一条",
                    "use_rag": False,
                    "use_sft": False,
                }
            ),
            content_type="application/json",
        )

        body = b"".join(response.streaming_content).decode("utf-8")
        first_user.refresh_from_db()
        last_user.refresh_from_db()
        self.assertIn("event: error", body)
        self.assertIn("只能修改或重新回答上一条用户消息", body)
        self.assertEqual(first_user.content, "第一条")
        self.assertEqual(last_user.content, "最后一条")
        self.assertTrue(Message.objects.filter(pk=first_assistant.pk).exists())
        self.assertTrue(Message.objects.filter(pk=last_assistant.pk).exists())

    def test_retry_last_user_message_returns_error_without_user_message(self) -> None:
        """没有任何用户消息时，重试接口应返回错误而不是创建新回答。"""
        conversation = Conversation.objects.create(title="空")

        response = Client().post(
            f"/api/conversations/{conversation.id}/last-user-message/retry",
            data=json.dumps(
                {
                    "message_id": 999,
                    "message": "新问题",
                    "use_rag": False,
                    "use_sft": False,
                }
            ),
            content_type="application/json",
        )

        body = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("event: error", body)
        self.assertIn("没有可修改的上一条用户消息", body)

    def test_ticket_is_generated_manually_for_conversation(self) -> None:
        """手动生成工单接口应根据已有会话消息生成一条 Ticket。"""
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
        self.assertEqual(generated.json()["payload"]["user_id"], f"conversation:{conversation.id}")

    def test_ticket_generation_is_idempotent_after_first_ticket(self) -> None:
        """工单生成应具备幂等性，防止同一会话反复点击生成多份工单。"""
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
        self.assertEqual(second.json()["payload"]["user_id"], f"conversation:{conversation.id}")

    def test_provider_health_api(self) -> None:
        """Provider health 接口应暴露默认模型和向量库配置。"""
        response = Client().get("/api/provider/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["chat_provider"], "ollama")
        self.assertEqual(response.json()["vector_provider"], "pgvector")

    def test_provider_health_respects_vector_provider_override(self) -> None:
        """环境变量覆盖向量库 provider 时，health 接口应反映覆盖结果。"""
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
        """FAISS 可用时，RAG 流式接口应先返回 citation，再返回模型 delta。"""
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
        """历史消息接口应返回已保存的引用，供前端重新打开会话时展示来源。"""
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
        """RAG 导入命令重复执行时应更新旧数据，而不是插入重复文档。"""
        output = StringIO()
        call_command("ingest_postal_rag", "--limit", "2", stdout=output)
        call_command("ingest_postal_rag", "--limit", "2", stdout=output)

        self.assertEqual(PostalDocument.objects.count(), 2)
        self.assertIn("documents_created=2", output.getvalue())
        self.assertIn("documents_updated=2", output.getvalue())

    def test_normalize_display_text_removes_chinese_spacing(self) -> None:
        """中文文本清理应去掉不自然空格，并保留正常标点。"""
        text = "用户 询问 邮寄 的 信息 ， 客服 回复 。"

        self.assertEqual(normalize_display_text(text), "用户询问邮寄的信息，客服回复。")

    def test_normalize_display_text_splits_dialogue_turns(self) -> None:
        """引用文本中连续的用户/客服轮次应拆成多行，方便前端阅读。"""
        text = "用户[0]: 你好客服[1]: 您好用户[2]: 查询一下"

        self.assertEqual(
            normalize_display_text(text),
            "用户[0]: 你好\n客服[1]: 您好\n用户[2]: 查询一下",
        )
