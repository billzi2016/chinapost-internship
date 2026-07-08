"""Django ORM 数据模型。

这里保存 Web 应用运行时状态：
- Conversation/Message：聊天历史；
- PostalDocument/PostalEmbedding：RAG 文档和向量；
- Citation：某条助手消息引用了哪些文档；
- Ticket：从会话生成的工单 JSON。

模型层只描述数据结构和最基础的查询便利属性；复杂业务流程放在 `apps.api.services`。
"""

from __future__ import annotations

from django.db import models
from pgvector.django import VectorField


EMBEDDING_DIMENSIONS = 4096


class Conversation(models.Model):
    """一次用户聊天会话。

    会话用于聚合多轮 Message、引用和工单。排序规则把置顶会话放前面，其余按更新时间倒序。
    """

    title = models.CharField(max_length=128, blank=True)
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """会话默认排序：置顶优先，其次按更新时间倒序。"""

        ordering = ["-is_pinned", "-updated_at"]

    def __str__(self) -> str:
        """Django admin 和调试输出中使用的可读名称。"""
        return self.title or f"会话 {self.pk}"

    @property
    def latest_error(self) -> str:
        """返回最近一次系统错误消息，供前端会话列表显示红色错误摘要。"""
        message = (
            self.messages.filter(role=Message.ROLE_SYSTEM, metadata__kind="error")
            .order_by("-created_at", "-id")
            .first()
        )
        return message.content if message else ""


class Message(models.Model):
    """会话中的单条消息。

    role 使用 OpenAI 风格的 user/assistant/system：
    - user：用户输入；
    - assistant：模型回答；
    - system：运行时错误或系统状态，不参与普通聊天展示逻辑。
    """

    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_SYSTEM = "system"
    ROLE_CHOICES = [
        (ROLE_USER, "用户"),
        (ROLE_ASSISTANT, "助手"),
        (ROLE_SYSTEM, "系统"),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=32, choices=ROLE_CHOICES)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """消息按创建顺序稳定排列。"""

        ordering = ["created_at", "id"]


class PostalDocument(models.Model):
    """导入到数据库中的邮政 RAG 文档切片。"""

    split = models.CharField(max_length=16)
    source_index = models.IntegerField()
    session_id = models.CharField(max_length=128)
    dialogue_id = models.IntegerField()
    source_path = models.TextField()
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """文档来源唯一性约束。"""

        # 同一来源切片只能入库一次；重复导入时靠这个约束避免产生重复 RAG 文档。
        constraints = [
            models.UniqueConstraint(
                fields=["split", "source_index", "session_id", "dialogue_id"],
                name="uniq_postal_document_source",
            )
        ]


class PostalEmbedding(models.Model):
    """PostalDocument 的向量表示。

    当前维度与已有 embedding 文件保持一致；如果更换 embedding 模型，必须同步迁移维度和数据。
    """

    document = models.OneToOneField(
        PostalDocument,
        on_delete=models.CASCADE,
        related_name="embedding",
    )
    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS)
    provider = models.CharField(max_length=64)
    model = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Citation(models.Model):
    """助手消息引用的 RAG 文档证据。"""

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="citations",
    )
    document = models.ForeignKey(
        PostalDocument,
        on_delete=models.CASCADE,
        related_name="citations",
        null=True,
        blank=True,
    )
    score = models.FloatField()
    quoted_text = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Ticket(models.Model):
    """从会话中抽取出的工单 JSON。

    工单生成后会锁定保存，避免用户多次点击导致同一会话出现多份不一致的工单。
    """

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="tickets",
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        related_name="tickets",
        null=True,
        blank=True,
    )
    payload = models.JSONField(default=dict)
    is_valid = models.BooleanField(default=False)
    validation_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
