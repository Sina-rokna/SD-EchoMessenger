import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.spaces.models import ChatSpace, Topic


def attachment_upload_path(instance: "Attachment", filename: str) -> str:
    """Never expose an uploader-controlled path or storage name."""
    suffix = Path(filename).suffix.lower()[:16]
    return (
        f"attachments/{instance.message.space_id}/"
        f"{instance.message_id}/{uuid.uuid4().hex}{suffix}"
    )


class Message(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        CANCELLED = "CANCELLED", "Cancelled"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_column="message_id",
    )
    space = models.ForeignKey(
        ChatSpace,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.PROTECT,
        related_name="messages",
        null=True,
        blank=True,
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sent_messages",
    )
    text = models.TextField(blank=True, db_column="content")
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.SENT,
    )
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    client_nonce = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("sent_at", "created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("sender", "client_nonce"),
                condition=models.Q(client_nonce__isnull=False),
                name="messaging_sender_client_nonce_unique",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status="PENDING", scheduled_for__isnull=False)
                    | ~models.Q(status="PENDING")
                ),
                name="messaging_pending_requires_schedule",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status="SENT", sent_at__isnull=False)
                    | ~models.Q(status="SENT")
                ),
                name="messaging_sent_requires_timestamp",
            ),
        ]
        indexes = [
            models.Index(fields=("space", "status", "sent_at")),
            models.Index(fields=("topic", "status", "sent_at")),
            models.Index(fields=("status", "scheduled_for")),
            models.Index(fields=("sender", "status", "scheduled_for")),
        ]

    @property
    def content(self) -> str:
        """Compatibility alias for the Phase-1 ERD's `content` name."""
        return self.text

    def clean(self):
        super().clean()
        if self.space_id:
            if self.space.type == ChatSpace.Type.CHANNEL:
                if not self.topic_id:
                    raise ValidationError(
                        {"topic": "Channel messages require a topic."}
                    )
                if self.topic.space_id != self.space_id:
                    raise ValidationError(
                        {"topic": "The topic belongs to another channel."}
                    )
            elif self.topic_id:
                raise ValidationError(
                    {"topic": "Direct and group messages cannot have a topic."}
                )
        if self.status == self.Status.PENDING and not self.scheduled_for:
            raise ValidationError(
                {"scheduled_for": "Pending messages require a delivery time."}
            )
        if self.status == self.Status.SENT and not self.sent_at:
            raise ValidationError({"sent_at": "Sent messages need a sent time."})

    def __str__(self) -> str:
        return f"{self.sender} in {self.space} at {self.created_at}"


class Attachment(models.Model):
    class Category(models.TextChoices):
        IMAGE = "IMAGE", "Image"
        VIDEO = "VIDEO", "Video"
        AUDIO = "AUDIO", "Audio"
        FILE = "FILE", "File"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(upload_to=attachment_upload_path, max_length=500)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=127)
    size = models.PositiveBigIntegerField()
    category = models.CharField(max_length=8, choices=Category.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)

    def __str__(self) -> str:
        return self.original_name
