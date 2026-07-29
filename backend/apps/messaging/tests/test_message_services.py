from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import override_settings
from django.utils import timezone

from apps.messaging.models import Message
from apps.messaging.services import (
    create_message,
    delete_sent_message,
    dispatch_scheduled_message,
)
from apps.notifications.models import Notification
from apps.spaces.models import ChatSpace, Role, SpaceMembership, Topic
from apps.spaces.services import create_space

User = get_user_model()


def make_users():
    alice = User.objects.create_user(
        username="alice",
        email="alice@example.com",
        password="SafePassword!123",
    )
    bob = User.objects.create_user(
        username="bob",
        email="bob@example.com",
        password="SafePassword!123",
    )
    return alice, bob


@pytest.mark.django_db(transaction=True)
def test_scheduled_dispatch_is_idempotent_and_creates_one_notification():
    alice, bob = make_users()
    space = create_space(
        actor=alice,
        space_type=ChatSpace.Type.GROUP,
        name="Study group",
        member_ids=[bob.pk],
    )
    message, _ = create_message(
        actor=alice,
        space=space,
        text="Due now",
        scheduled_for=timezone.now() + timedelta(hours=1),
    )
    Message.objects.filter(pk=message.pk).update(
        scheduled_for=timezone.now() - timedelta(seconds=1)
    )

    first = dispatch_scheduled_message(message.pk)
    second = dispatch_scheduled_message(message.pk)

    message.refresh_from_db()
    assert first is True
    assert second is False
    assert message.status == Message.Status.SENT
    assert Notification.objects.filter(recipient=bob, message=message).count() == 1


@pytest.mark.django_db(transaction=True)
def test_scheduled_dispatch_rechecks_revoked_channel_permission():
    alice, bob = make_users()
    space = create_space(
        actor=alice,
        space_type=ChatSpace.Type.CHANNEL,
        name="Engineering",
        member_ids=[bob.pk],
    )
    topic = Topic.objects.create(space=space, name="General", created_by=alice)
    message, _ = create_message(
        actor=bob,
        space=space,
        topic=topic,
        text="Permission may change",
        scheduled_for=timezone.now() + timedelta(hours=1),
    )
    denied_role = Role.objects.create(
        space=space,
        name="Muted",
        can_send_messages=False,
        can_send_media=False,
    )
    SpaceMembership.objects.filter(space=space, user=bob).update(role=denied_role)
    Message.objects.filter(pk=message.pk).update(
        scheduled_for=timezone.now() - timedelta(seconds=1)
    )

    result = dispatch_scheduled_message(message.pk)

    message.refresh_from_db()
    assert result is False
    assert message.status == Message.Status.FAILED
    assert "permission" in message.failure_reason.lower()
    assert not Notification.objects.filter(message=message).exists()


@pytest.mark.django_db(transaction=True)
def test_hard_delete_removes_attachment_from_storage(tmp_path):
    alice, bob = make_users()
    space = create_space(
        actor=alice,
        space_type=ChatSpace.Type.GROUP,
        name="Study group",
        member_ids=[bob.pk],
    )
    with override_settings(MEDIA_ROOT=tmp_path):
        message, _ = create_message(
            actor=alice,
            space=space,
            files=[
                SimpleUploadedFile(
                    "notes.txt",
                    b"temporary",
                    content_type="text/plain",
                )
            ],
        )
        attachment = message.attachments.get()
        storage = attachment.file.storage
        stored_name = attachment.file.name
        assert storage.exists(stored_name)

        delete_sent_message(actor=alice, message=message)

        assert not storage.exists(stored_name)


@pytest.mark.django_db(transaction=True)
def test_duplicate_nonce_race_recovers_after_inner_savepoint():
    alice, bob = make_users()
    space = create_space(
        actor=alice,
        space_type=ChatSpace.Type.GROUP,
        name="Study group",
        member_ids=[bob.pk],
    )
    nonce = uuid4()
    existing = Message.objects.create(
        sender=alice,
        space=space,
        text="Winner",
        status=Message.Status.SENT,
        sent_at=timezone.now(),
        client_nonce=nonce,
    )

    with (
        patch.object(Message.objects, "filter") as filtered,
        patch.object(Message, "full_clean"),
        patch.object(
            Message,
            "save",
            side_effect=IntegrityError("simulated concurrent insert"),
        ),
    ):
        filtered.return_value.select_related.return_value.first.return_value = None
        resolved, created = create_message(
            actor=alice,
            space=space,
            text="Retry",
            client_nonce=nonce,
        )

    assert resolved == existing
    assert created is False
