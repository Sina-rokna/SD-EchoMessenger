from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.messaging.models import Message
from apps.messaging.tasks import dispatch_due_messages
from apps.notifications.models import Notification
from apps.spaces.models import ChatSpace, SpaceMembership

User = get_user_model()


def make_group_with_two_members():
    sender = User.objects.create_user(
        username="scheduler",
        email="scheduler@example.com",
        password="StrongPassword123!",
    )
    recipient = User.objects.create_user(
        username="receiver",
        email="receiver@example.com",
        password="StrongPassword123!",
    )
    space = ChatSpace.objects.create(
        name="Scheduled group",
        type=ChatSpace.Type.GROUP,
        created_by=sender,
    )
    SpaceMembership.objects.bulk_create(
        [
            SpaceMembership(space=space, user=sender),
            SpaceMembership(space=space, user=recipient),
        ]
    )
    return sender, recipient, space


def pending_message(*, sender, space, scheduled_for):
    return Message.objects.create(
        sender=sender,
        space=space,
        text="This message was scheduled.",
        status=Message.Status.PENDING,
        scheduled_for=scheduled_for,
    )


@pytest.mark.django_db(transaction=True)
def test_due_message_is_sent_once_with_notification_and_event():
    sender, recipient, space = make_group_with_two_members()
    message = pending_message(
        sender=sender,
        space=space,
        scheduled_for=timezone.now() - timedelta(seconds=1),
    )

    with (
        patch("apps.messaging.realtime.broadcast_space_event") as space_event,
        patch("apps.messaging.realtime.broadcast_user_event"),
    ):
        first = dispatch_due_messages.run()
        second = dispatch_due_messages.run()

    message.refresh_from_db()
    assert first == {"candidates": 1, "sent": 1, "skipped": 0}
    assert second == {"candidates": 0, "sent": 0, "skipped": 0}
    assert message.status == Message.Status.SENT
    assert message.sent_at is not None
    assert message.failure_reason == ""

    notifications = Notification.objects.filter(
        message=message,
        recipient=recipient,
        event_type=Notification.EventType.MESSAGE_CREATED,
    )
    assert notifications.count() == 1
    space_event.assert_called_once()
    assert space_event.call_args.args[0] == str(space.pk)
    assert space_event.call_args.args[1] == "scheduled_message.sent"


@pytest.mark.django_db(transaction=True)
def test_future_message_is_not_dispatched():
    sender, _, space = make_group_with_two_members()
    message = pending_message(
        sender=sender,
        space=space,
        scheduled_for=timezone.now() + timedelta(hours=1),
    )

    result = dispatch_due_messages.run()

    message.refresh_from_db()
    assert result == {"candidates": 0, "sent": 0, "skipped": 0}
    assert message.status == Message.Status.PENDING
    assert message.sent_at is None


@pytest.mark.django_db(transaction=True)
def test_dispatch_rechecks_sender_membership():
    sender, _, space = make_group_with_two_members()
    message = pending_message(
        sender=sender,
        space=space,
        scheduled_for=timezone.now() - timedelta(seconds=1),
    )
    SpaceMembership.objects.filter(space=space, user=sender).delete()

    result = dispatch_due_messages.run()

    message.refresh_from_db()
    assert result == {"candidates": 1, "sent": 0, "skipped": 1}
    assert message.status == Message.Status.FAILED
    assert message.sent_at is None
    assert "permission" in message.failure_reason.lower()
    assert not Notification.objects.filter(message=message).exists()
