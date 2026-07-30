import uuid

from django.conf import settings
from django.db import models

from apps.messaging.models import Message
from apps.spaces.models import ChatSpace


class Notification(models.Model):
    class EventType(models.TextChoices):
        MESSAGE_CREATED = "MESSAGE_CREATED", "New message"
        MEMBER_ADDED = "MEMBER_ADDED", "Added to a space"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="triggered_notifications",
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    space = models.ForeignKey(
        ChatSpace,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        related_name="notifications",
        null=True,
        blank=True,
    )
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("recipient", "message", "event_type"),
                condition=models.Q(message__isnull=False),
                name="notifications_one_event_per_message_recipient",
            ),
        ]
        indexes = [
            models.Index(fields=("recipient", "read_at", "created_at")),
        ]

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    def __str__(self) -> str:
        return f"{self.event_type} for {self.recipient}"
