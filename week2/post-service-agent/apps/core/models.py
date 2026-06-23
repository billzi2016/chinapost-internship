from __future__ import annotations

from django.db import models


class Conversation(models.Model):
    title = models.CharField(max_length=128, blank=True)
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_pinned", "-updated_at"]

    def __str__(self) -> str:
        return self.title or f"会话 {self.pk}"

    @property
    def latest_error(self) -> str:
        message = (
            self.messages.filter(role=Message.ROLE_SYSTEM, metadata__kind="error")
            .order_by("-created_at", "-id")
            .first()
        )
        return message.content if message else ""


class Message(models.Model):
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
        ordering = ["created_at", "id"]


class PostalDocument(models.Model):
    split = models.CharField(max_length=16)
    source_index = models.IntegerField()
    session_id = models.CharField(max_length=128)
    dialogue_id = models.IntegerField()
    source_path = models.TextField()
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["split", "source_index", "session_id", "dialogue_id"],
                name="uniq_postal_document_source",
            )
        ]


class Citation(models.Model):
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
