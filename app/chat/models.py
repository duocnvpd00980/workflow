# chat/models.py

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class ConversationQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_archived=False)

    def for_user(self, user):
        return self.filter(user=user)


class Conversation(models.Model):
    """
    One conversation/thread per chat session.

    LangGraph thread_id:
        conv_<conversation.id>

    Example:
        conv_0c5a89d2-0e22-4f9d-a7c7-f9c26b4d4e91
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_conversations",
    )

    title = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    system_prompt = models.TextField(
        blank=True,
        default="",
    )

    is_archived = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    last_message_at = models.DateTimeField(
        default=timezone.now,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    objects = ConversationQuerySet.as_manager()

    class Meta:
        ordering = ["-last_message_at"]
        indexes = [
            models.Index(fields=["user", "-last_message_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return self.title or f"Conversation {self.id}"

    @property
    def thread_id(self) -> str:
        return f"conv_{self.id}"

    def touch(self):
        self.last_message_at = timezone.now()
        self.save(update_fields=["last_message_at", "updated_at"])


class Message(models.Model):
    """
    Immutable message timeline.

    UI should render from this table,
    NOT from LangGraph snapshots.
    """

    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"
        TOOL = "tool", "Tool"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        STREAMING = "streaming", "Streaming"
        COMPLETED = "completed", "Completed"
        ERROR = "error", "Error"
        INTERRUPTED = "interrupted", "Interrupted"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.COMPLETED,
    )

    content = models.TextField(
        blank=True,
        default="",
    )

    html = models.TextField(
        blank=True,
        default="",
    )

    node_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    token_input = models.PositiveIntegerField(
        default=0,
    )

    token_output = models.PositiveIntegerField(
        default=0,
    )

    model_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    error_message = models.TextField(
        blank=True,
        default="",
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["role"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.role} • {self.created_at:%Y-%m-%d %H:%M:%S}"


class ConversationMemory(models.Model):
    """
    Optional long-term memory layer.

    Useful for:
    - user preferences
    - summaries
    - extracted facts
    - embeddings
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="memories",
    )

    key = models.CharField(
        max_length=255,
    )

    value = models.JSONField(
        default=dict,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        unique_together = ("conversation", "key")
        indexes = [
            models.Index(fields=["conversation", "key"]),
        ]

    def __str__(self):
        return self.key
