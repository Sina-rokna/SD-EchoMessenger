from __future__ import annotations

import mimetypes
from pathlib import Path

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.spaces.models import ChatSpace, Topic
from apps.spaces.services import (
    can_send_messages,
    is_member,
    require_member,
)

from .models import Attachment, Message

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".mp4",
    ".webm",
    ".mov",
    ".mp3",
    ".wav",
    ".ogg",
    ".m4a",
    ".pdf",
    ".txt",
    ".csv",
    ".zip",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
}

ALLOWED_GENERAL_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/csv",
    "application/zip",
    "application/x-zip-compressed",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def _safe_original_name(name: str) -> str:
    safe = Path(name).name.replace("\x00", "").strip()
    if not safe:
        safe = "attachment"
    return safe[:255]


def validate_attachment(upload) -> dict:
    name = _safe_original_name(upload.name)
    extension = Path(name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            {
                "attachments": (
                    f"{name} has an unsupported file extension."
                )
            }
        )
    if upload.size <= 0:
        raise ValidationError({"attachments": f"{name} is empty."})
    if upload.size > settings.MAX_ATTACHMENT_SIZE:
        maximum_mib = settings.MAX_ATTACHMENT_SIZE / (1024 * 1024)
        size_label = (
            str(int(maximum_mib))
            if maximum_mib.is_integer()
            else f"{maximum_mib:.1f}"
        )
        raise ValidationError(
            {"attachments": f"{name} is larger than {size_label} MiB."}
        )

    declared_type = (
        getattr(upload, "content_type", None)
        or mimetypes.guess_type(name)[0]
        or "application/octet-stream"
    ).lower()
    guessed_type = mimetypes.guess_type(name)[0]
    if guessed_type:
        declared_family = declared_type.split("/", 1)[0]
        guessed_family = guessed_type.split("/", 1)[0]
        if declared_family != guessed_family and declared_type not in {
            "application/octet-stream",
            "application/zip",
            "application/x-zip-compressed",
        }:
            raise ValidationError(
                {
                    "attachments": (
                        f"{name} does not match its declared content type."
                    )
                }
            )

    if declared_type.startswith("image/"):
        category = Attachment.Category.IMAGE
    elif declared_type.startswith("video/"):
        category = Attachment.Category.VIDEO
    elif declared_type.startswith("audio/"):
        category = Attachment.Category.AUDIO
    elif declared_type in ALLOWED_GENERAL_MIME_TYPES:
        category = Attachment.Category.FILE
    else:
        raise ValidationError(
            {"attachments": f"{name} has an unsupported content type."}
        )
    return {
        "file": upload,
        "original_name": name,
        "content_type": declared_type,
        "size": upload.size,
        "category": category,
    }


def validate_message_target(space: ChatSpace, topic: Topic | None):
    if space.type == ChatSpace.Type.CHANNEL:
        if not topic:
            raise ValidationError(
                {"topic_id": "Channel messages require a topic."}
            )
        if topic.space_id != space.pk:
            raise ValidationError(
                {"topic_id": "The topic belongs to another channel."}
            )
    elif topic:
        raise ValidationError(
            {"topic_id": "Direct and group messages cannot have a topic."}
        )


def serialize_message(message: Message) -> dict:
    """Build the stable API/event payload without needing an HTTP request."""
    from .serializers import MessageSerializer

    message = (
        Message.objects.select_related("sender", "space", "topic")
        .prefetch_related("attachments")
        .get(pk=message.pk)
    )
    return MessageSerializer(message).data


def _schedule_message_event(
    message: Message,
    event_type: str,
    *,
    payload: dict | None = None,
):
    space_id = str(message.space_id)
    message_id = message.pk

    def publish():
        from apps.messaging.realtime import broadcast_space_event

        event_payload = payload or serialize_message(
            Message.objects.get(pk=message_id)
        )
        broadcast_space_event(space_id, event_type, event_payload)

    transaction.on_commit(publish)


def _notify_message_members(message: Message):
    from apps.notifications.services import create_message_notifications

    create_message_notifications(message)


@transaction.atomic
def create_message(
    *,
    actor,
    space: ChatSpace,
    text: str = "",
    topic: Topic | None = None,
    files=(),
    scheduled_for=None,
    client_nonce=None,
) -> tuple[Message, bool]:
    require_member(actor, space)
    files = list(files)
    if len(files) > settings.MAX_ATTACHMENTS_PER_MESSAGE:
        raise ValidationError(
            {
                "attachments": (
                    "At most "
                    f"{settings.MAX_ATTACHMENTS_PER_MESSAGE} files are allowed."
                )
            }
        )
    text = text.strip()
    if not text and not files:
        raise ValidationError(
            {"text": "A message needs text or at least one attachment."}
        )
    validate_message_target(space, topic)
    if not can_send_messages(actor, space, has_attachments=bool(files)):
        raise PermissionDenied("Your channel role cannot send this message.")

    attachment_data = [validate_attachment(upload) for upload in files]
    if scheduled_for and scheduled_for <= timezone.now():
        raise ValidationError(
            {"scheduled_for": "The delivery time must be in the future."}
        )

    if client_nonce:
        existing = (
            Message.objects.filter(sender=actor, client_nonce=client_nonce)
            .select_related("space")
            .first()
        )
        if existing:
            if existing.space_id != space.pk:
                raise ValidationError(
                    {"client_nonce": "This nonce was used in another space."}
                )
            return existing, False

    is_scheduled = scheduled_for is not None
    message = Message(
        sender=actor,
        space=space,
        topic=topic,
        text=text,
        status=(
            Message.Status.PENDING
            if is_scheduled
            else Message.Status.SENT
        ),
        scheduled_for=scheduled_for,
        sent_at=None if is_scheduled else timezone.now(),
        client_nonce=client_nonce,
    )
    message.full_clean()
    try:
        # Keep the outer transaction usable if a concurrent request wins the
        # sender/client-nonce uniqueness race.
        with transaction.atomic():
            message.save()
    except IntegrityError as exc:
        if not client_nonce:
            raise
        existing = Message.objects.get(sender=actor, client_nonce=client_nonce)
        if existing.space_id != space.pk:
            raise ValidationError(
                {"client_nonce": "This nonce was used in another space."}
            ) from exc
        return existing, False

    for metadata in attachment_data:
        Attachment.objects.create(message=message, **metadata)

    if not is_scheduled:
        ChatSpace.objects.filter(pk=space.pk).update(updated_at=timezone.now())
        _notify_message_members(message)
        _schedule_message_event(message, "message.created")
    return message, True


@transaction.atomic
def edit_sent_message(*, actor, message: Message, text: str) -> Message:
    if message.sender_id != actor.pk:
        raise PermissionDenied("Only the sender may edit a message.")
    if message.status != Message.Status.SENT:
        raise ValidationError("Use the scheduled-message endpoint for this message.")
    text = text.strip()
    if not text and not message.attachments.exists():
        raise ValidationError(
            {"text": "A message needs text or at least one attachment."}
        )
    message.text = text
    message.edited_at = timezone.now()
    message.save(update_fields=("text", "edited_at"))
    _schedule_message_event(message, "message.updated")
    return message


@transaction.atomic
def delete_sent_message(*, actor, message: Message):
    from apps.spaces.services import can_delete_message

    if message.status != Message.Status.SENT:
        raise ValidationError("Use the scheduled-message endpoint for this message.")
    if not can_delete_message(actor, message):
        raise PermissionDenied("You cannot delete this message.")
    payload = {
        "id": str(message.pk),
        "space_id": str(message.space_id),
    }
    _schedule_message_event(message, "message.deleted", payload=payload)
    message.delete()


@transaction.atomic
def update_scheduled_message(
    *,
    actor,
    message: Message,
    text=None,
    topic=None,
    scheduled_for=None,
) -> Message:
    message = Message.objects.select_for_update().get(pk=message.pk)
    if message.sender_id != actor.pk:
        raise PermissionDenied("Only the sender may edit a scheduled message.")
    if message.status != Message.Status.PENDING:
        raise ValidationError("This message is no longer pending.")

    if text is not None:
        message.text = text.strip()
    if topic is not None:
        message.topic = topic
    if scheduled_for is not None:
        if scheduled_for <= timezone.now():
            raise ValidationError(
                {"scheduled_for": "The delivery time must be in the future."}
            )
        message.scheduled_for = scheduled_for
    if not message.text and not message.attachments.exists():
        raise ValidationError(
            {"text": "A message needs text or at least one attachment."}
        )
    validate_message_target(message.space, message.topic)
    if not can_send_messages(
        actor,
        message.space,
        has_attachments=message.attachments.exists(),
    ):
        raise PermissionDenied("Your channel role cannot send this message.")
    message.full_clean()
    message.save(
        update_fields=("text", "topic", "scheduled_for"),
    )
    return message


@transaction.atomic
def cancel_scheduled_message(*, actor, message: Message):
    message = Message.objects.select_for_update().get(pk=message.pk)
    if message.sender_id != actor.pk:
        raise PermissionDenied("Only the sender may cancel a scheduled message.")
    if message.status != Message.Status.PENDING:
        raise ValidationError("This message is no longer pending.")
    message.status = Message.Status.CANCELLED
    message.save(update_fields=("status",))


@transaction.atomic
def dispatch_scheduled_message(message_id) -> bool:
    """
    Atomically deliver one due message.

    The status guard makes retries idempotent. Celery may safely call this
    function more than once after a worker restart.
    """
    message = (
        Message.objects.select_for_update()
        .select_related("space", "sender", "topic")
        .prefetch_related("attachments")
        .filter(pk=message_id)
        .first()
    )
    if not message or message.status != Message.Status.PENDING:
        return False
    if not message.scheduled_for or message.scheduled_for > timezone.now():
        return False

    has_attachments = bool(message.attachments.all())
    if not is_member(message.sender, message.space) or not can_send_messages(
        message.sender,
        message.space,
        has_attachments=has_attachments,
    ):
        message.status = Message.Status.FAILED
        message.failure_reason = "The sender no longer has permission to send."
        message.save(update_fields=("status", "failure_reason"))
        return False

    try:
        validate_message_target(message.space, message.topic)
    except ValidationError:
        message.status = Message.Status.FAILED
        message.failure_reason = "The selected topic is no longer available."
        message.save(update_fields=("status", "failure_reason"))
        return False

    message.status = Message.Status.SENT
    message.sent_at = timezone.now()
    message.failure_reason = ""
    message.save(update_fields=("status", "sent_at", "failure_reason"))
    ChatSpace.objects.filter(pk=message.space_id).update(updated_at=message.sent_at)
    _notify_message_members(message)
    _schedule_message_event(message, "scheduled_message.sent")
    return True
