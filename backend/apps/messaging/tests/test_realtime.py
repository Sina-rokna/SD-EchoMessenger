from unittest.mock import patch

import pytest
from asgiref.sync import async_to_sync, sync_to_async
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import Client

from apps.messaging.realtime import (
    broadcast_space_event,
    broadcast_user_event,
    publish_space_event_on_commit,
)
from apps.spaces.models import ChatSpace, SpaceMembership
from config.asgi import application

User = get_user_model()


def session_headers(user) -> list[tuple[bytes, bytes]]:
    client = Client()
    client.force_login(user)
    session_id = client.cookies[settings.SESSION_COOKIE_NAME].value
    return [
        (
            b"cookie",
            f"{settings.SESSION_COOKIE_NAME}={session_id}".encode(),
        ),
        (b"origin", b"http://localhost"),
    ]


@pytest.mark.django_db(transaction=True)
def test_event_publication_waits_for_commit_and_ignores_rollbacks():
    space_id = "2fe35e45-f5e0-4b9a-b1e3-86ab2d581515"

    with patch("apps.messaging.realtime.broadcast_space_event") as broadcast:
        with transaction.atomic():
            publish_space_event_on_commit(
                space_id,
                "space.updated",
                {"id": space_id},
            )
            broadcast.assert_not_called()
        broadcast.assert_called_once_with(
            space_id,
            "space.updated",
            {"id": space_id},
        )

    with patch("apps.messaging.realtime.broadcast_space_event") as broadcast:
        with pytest.raises(RuntimeError), transaction.atomic():
            publish_space_event_on_commit(
                space_id,
                "space.updated",
                {"id": space_id},
            )
            raise RuntimeError("force rollback")
        broadcast.assert_not_called()


@pytest.mark.django_db(transaction=True)
def test_space_socket_rejects_anonymous_and_nonmembers():
    owner = User.objects.create_user(
        username="owner",
        email="owner@example.com",
        password="StrongPassword123!",
    )
    outsider = User.objects.create_user(
        username="outsider",
        email="outsider@example.com",
        password="StrongPassword123!",
    )
    space = ChatSpace.objects.create(
        name="Private group",
        type=ChatSpace.Type.GROUP,
        created_by=owner,
    )
    SpaceMembership.objects.create(space=space, user=owner)
    outsider_headers = session_headers(outsider)

    async def exercise():
        anonymous = WebsocketCommunicator(
            application,
            f"/ws/spaces/{space.pk}/",
            headers=[(b"origin", b"http://localhost")],
        )
        connected, close_code = await anonymous.connect()
        assert connected is False
        assert close_code == 4401

        nonmember = WebsocketCommunicator(
            application,
            f"/ws/spaces/{space.pk}/",
            headers=outsider_headers,
        )
        connected, close_code = await nonmember.connect()
        assert connected is False
        assert close_code == 4403

    async_to_sync(exercise)()


@pytest.mark.django_db(transaction=True)
def test_member_receives_committed_space_event():
    member = User.objects.create_user(
        username="member",
        email="member@example.com",
        password="StrongPassword123!",
    )
    space = ChatSpace.objects.create(
        name="Live group",
        type=ChatSpace.Type.GROUP,
        created_by=member,
    )
    SpaceMembership.objects.create(space=space, user=member)
    headers = session_headers(member)

    async def exercise():
        communicator = WebsocketCommunicator(
            application,
            f"/ws/spaces/{space.pk}/",
            headers=headers,
        )
        connected, _ = await communicator.connect()
        assert connected is True

        await communicator.send_json_to({"type": "ping"})
        assert await communicator.receive_json_from() == {"type": "pong"}

        await sync_to_async(broadcast_space_event, thread_sensitive=False)(
            space.pk,
            "message.created",
            {"id": "example-message"},
        )
        event = await communicator.receive_json_from()
        assert event["type"] == "message.created"
        assert event["payload"] == {"id": "example-message"}
        assert event["event_id"]
        assert event["occurred_at"].endswith("Z")
        await communicator.disconnect()

    async_to_sync(exercise)()


@pytest.mark.django_db(transaction=True)
def test_notification_socket_is_personal():
    recipient = User.objects.create_user(
        username="recipient",
        email="recipient@example.com",
        password="StrongPassword123!",
    )
    other = User.objects.create_user(
        username="other",
        email="other@example.com",
        password="StrongPassword123!",
    )
    headers = session_headers(recipient)

    async def exercise():
        communicator = WebsocketCommunicator(
            application,
            "/ws/notifications/",
            headers=headers,
        )
        connected, _ = await communicator.connect()
        assert connected is True

        await sync_to_async(broadcast_user_event, thread_sensitive=False)(
            other.pk,
            "notification.created",
            {"id": "not-for-recipient"},
        )
        assert await communicator.receive_nothing(timeout=0.05)

        await sync_to_async(broadcast_user_event, thread_sensitive=False)(
            recipient.pk,
            "notification.created",
            {"id": "for-recipient"},
        )
        event = await communicator.receive_json_from()
        assert event["type"] == "notification.created"
        assert event["payload"]["id"] == "for-recipient"
        await communicator.disconnect()

    async_to_sync(exercise)()
