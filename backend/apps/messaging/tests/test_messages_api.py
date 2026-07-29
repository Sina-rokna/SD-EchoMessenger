from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.messaging.models import Message
from apps.spaces.models import ChatSpace, Role, SpaceMembership, Topic
from apps.spaces.services import create_space, get_or_create_direct_space

User = get_user_model()


@pytest.fixture
def users(db):
    return [
        User.objects.create_user(
            username=name,
            email=f"{name}@example.com",
            password="SafePassword!123",
        )
        for name in ("alice", "bob", "carol")
    ]


def authenticated(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def group_with_members(owner, *members):
    return create_space(
        actor=owner,
        space_type=ChatSpace.Type.GROUP,
        name="Study group",
        member_ids=[member.pk for member in members],
    )


def channel_with_members(owner, *members):
    return create_space(
        actor=owner,
        space_type=ChatSpace.Type.CHANNEL,
        name="Engineering",
        member_ids=[member.pk for member in members],
    )


@pytest.mark.django_db
def test_send_history_and_persistent_notification(users):
    alice, bob, _ = users
    space = group_with_members(alice, bob)

    sent = authenticated(alice).post(
        f"/api/v1/spaces/{space.pk}/messages/",
        {"text": "Hello, Bob!"},
        format="json",
    )
    history = authenticated(bob).get(
        f"/api/v1/spaces/{space.pk}/messages/"
    )

    assert sent.status_code == 201
    assert sent.data["status"] == "SENT"
    assert history.status_code == 200
    assert [item["text"] for item in history.data["results"]] == ["Hello, Bob!"]
    assert bob.notifications.filter(message_id=sent.data["id"]).count() == 1


@pytest.mark.django_db
def test_first_history_page_contains_newest_messages(users):
    alice, bob, _ = users
    space = group_with_members(alice, bob)
    base_time = timezone.now() - timedelta(minutes=55)
    messages = Message.objects.bulk_create(
        Message(
            sender=alice,
            space=space,
            text=f"message {index}",
            status=Message.Status.SENT,
            sent_at=base_time + timedelta(minutes=index),
        )
        for index in range(55)
    )

    first_page = authenticated(bob).get(
        f"/api/v1/spaces/{space.pk}/messages/"
    )
    second_page = authenticated(bob).get(
        f"/api/v1/spaces/{space.pk}/messages/?page=2"
    )

    assert first_page.status_code == 200
    assert len(first_page.data["results"]) == 50
    assert first_page.data["results"][0]["id"] == str(messages[54].pk)
    assert first_page.data["results"][-1]["id"] == str(messages[5].pk)
    assert [item["id"] for item in second_page.data["results"]] == [
        str(message.pk) for message in reversed(messages[:5])
    ]


@pytest.mark.django_db
def test_message_requires_text_or_attachment(users):
    alice, bob, _ = users
    space = group_with_members(alice, bob)

    response = authenticated(alice).post(
        f"/api/v1/spaces/{space.pk}/messages/",
        {"text": "   "},
        format="json",
    )

    assert response.status_code == 400
    assert "text" in response.data


@pytest.mark.django_db
def test_only_sender_can_edit_but_group_member_can_delete(users):
    alice, bob, _ = users
    space = group_with_members(alice, bob)
    sent = authenticated(alice).post(
        f"/api/v1/spaces/{space.pk}/messages/",
        {"text": "Original"},
        format="json",
    )
    url = f"/api/v1/messages/{sent.data['id']}/"

    forbidden_edit = authenticated(bob).patch(
        url,
        {"text": "Taken over"},
        format="json",
    )
    edited = authenticated(alice).patch(
        url,
        {"text": "Corrected"},
        format="json",
    )
    deleted = authenticated(bob).delete(url)

    assert forbidden_edit.status_code == 403
    assert edited.status_code == 200
    assert edited.data["is_edited"] is True
    assert edited.data["text"] == "Corrected"
    assert deleted.status_code == 204
    assert not Message.objects.filter(pk=sent.data["id"]).exists()


@pytest.mark.django_db
def test_direct_recipient_cannot_delete_sender_message(users):
    alice, bob, _ = users
    space, _ = get_or_create_direct_space(alice, bob)
    sent = authenticated(alice).post(
        f"/api/v1/spaces/{space.pk}/messages/",
        {"text": "Private"},
        format="json",
    )

    response = authenticated(bob).delete(
        f"/api/v1/messages/{sent.data['id']}/"
    )

    assert response.status_code == 403
    assert Message.objects.filter(pk=sent.data["id"]).exists()


@pytest.mark.django_db
def test_channel_messages_require_topic(users):
    alice, bob, _ = users
    space = channel_with_members(alice, bob)
    topic = Topic.objects.create(
        space=space,
        name="Backend",
        created_by=alice,
    )

    missing_topic = authenticated(bob).post(
        f"/api/v1/spaces/{space.pk}/messages/",
        {"text": "Where should this go?"},
        format="json",
    )
    valid = authenticated(bob).post(
        f"/api/v1/spaces/{space.pk}/messages/",
        {"text": "API update", "topic_id": str(topic.pk)},
        format="json",
    )

    assert missing_topic.status_code == 400
    assert valid.status_code == 201
    assert valid.data["topic_id"] == str(topic.pk)


@pytest.mark.django_db
def test_channel_manager_can_delete_another_users_message(users):
    alice, bob, carol = users
    space = channel_with_members(alice, bob, carol)
    topic = Topic.objects.create(space=space, name="General", created_by=alice)
    moderator = Role.objects.create(
        space=space,
        name="Moderator",
        can_send_messages=True,
        can_send_media=True,
        can_delete_messages=True,
    )
    membership = SpaceMembership.objects.get(space=space, user=carol)
    membership.role = moderator
    membership.save(update_fields=("role",))
    sent = authenticated(bob).post(
        f"/api/v1/spaces/{space.pk}/messages/",
        {"text": "Moderate this", "topic_id": str(topic.pk)},
        format="json",
    )

    response = authenticated(carol).delete(
        f"/api/v1/messages/{sent.data['id']}/"
    )

    assert response.status_code == 204


@pytest.mark.django_db
def test_message_search_is_scoped_to_requested_membership(users):
    alice, bob, carol = users
    first = group_with_members(alice, bob)
    second = group_with_members(alice, carol)
    authenticated(alice).post(
        f"/api/v1/spaces/{first.pk}/messages/",
        {"text": "secret alpha"},
        format="json",
    )
    authenticated(alice).post(
        f"/api/v1/spaces/{second.pk}/messages/",
        {"text": "secret beta"},
        format="json",
    )

    visible = authenticated(bob).get(
        f"/api/v1/spaces/{first.pk}/messages/search/?q=secret"
    )
    hidden = authenticated(bob).get(
        f"/api/v1/spaces/{second.pk}/messages/search/?q=secret"
    )

    assert [item["text"] for item in visible.data["results"]] == ["secret alpha"]
    assert hidden.status_code == 404


@pytest.mark.django_db
def test_role_without_media_permission_is_enforced_server_side(users):
    alice, bob, _ = users
    space = channel_with_members(alice, bob)
    topic = Topic.objects.create(space=space, name="General", created_by=alice)
    text_only = Role.objects.create(
        space=space,
        name="Text only",
        can_send_messages=True,
        can_send_media=False,
    )
    SpaceMembership.objects.filter(space=space, user=bob).update(role=text_only)
    upload = SimpleUploadedFile(
        "photo.png",
        b"not-a-real-image-but-valid-for-storage-tests",
        content_type="image/png",
    )

    response = authenticated(bob).post(
        f"/api/v1/spaces/{space.pk}/messages/",
        {
            "text": "blocked upload",
            "topic_id": str(topic.pk),
            "attachments": [upload],
        },
        format="multipart",
    )

    assert response.status_code == 403
    assert not Message.objects.filter(space=space).exists()


@pytest.mark.django_db
def test_attachment_validation_rejects_extension_and_size(users):
    alice, bob, _ = users
    space = group_with_members(alice, bob)
    executable = SimpleUploadedFile(
        "payload.exe",
        b"MZ",
        content_type="application/octet-stream",
    )
    invalid_extension = authenticated(alice).post(
        f"/api/v1/spaces/{space.pk}/messages/",
        {"attachments": [executable]},
        format="multipart",
    )

    with override_settings(MAX_ATTACHMENT_SIZE=3):
        too_large = authenticated(alice).post(
            f"/api/v1/spaces/{space.pk}/messages/",
            {
                "attachments": [
                    SimpleUploadedFile(
                        "notes.txt",
                        b"four",
                        content_type="text/plain",
                    )
                ]
            },
            format="multipart",
        )

    assert invalid_extension.status_code == 400
    assert too_large.status_code == 400


@pytest.mark.django_db
def test_attachment_download_requires_membership(users, tmp_path):
    alice, bob, carol = users
    space = group_with_members(alice, bob)
    with override_settings(MEDIA_ROOT=tmp_path):
        sent = authenticated(alice).post(
            f"/api/v1/spaces/{space.pk}/messages/",
            {
                "attachments": [
                    SimpleUploadedFile(
                        "notes.txt",
                        b"course notes",
                        content_type="text/plain",
                    )
                ]
            },
            format="multipart",
        )
        attachment_id = sent.data["attachments"][0]["id"]
        allowed = authenticated(bob).get(
            f"/api/v1/attachments/{attachment_id}/download/"
        )
        denied = authenticated(carol).get(
            f"/api/v1/attachments/{attachment_id}/download/"
        )

        assert allowed.status_code == 200
        assert allowed["Content-Type"] == "text/plain"
        assert allowed["Content-Disposition"].startswith("inline")
        assert allowed["X-Content-Type-Options"] == "nosniff"
        assert denied.status_code == 404
        allowed.close()


@pytest.mark.django_db
def test_scheduled_message_is_hidden_from_history_and_listed_for_sender(users):
    alice, bob, _ = users
    space = group_with_members(alice, bob)
    delivery = timezone.now() + timedelta(hours=1)

    scheduled = authenticated(alice).post(
        f"/api/v1/spaces/{space.pk}/messages/",
        {"text": "Send later", "scheduled_for": delivery.isoformat()},
        format="json",
    )
    history = authenticated(bob).get(
        f"/api/v1/spaces/{space.pk}/messages/"
    )
    outbox = authenticated(alice).get("/api/v1/scheduled-messages/")

    assert scheduled.status_code == 201
    assert scheduled.data["status"] == "PENDING"
    assert history.data["results"] == []
    assert [item["id"] for item in outbox.data["results"]] == [
        scheduled.data["id"]
    ]


@pytest.mark.django_db
def test_sender_can_update_and_cancel_scheduled_message(users):
    alice, bob, _ = users
    space = group_with_members(alice, bob)
    delivery = timezone.now() + timedelta(hours=1)
    scheduled = authenticated(alice).post(
        f"/api/v1/spaces/{space.pk}/messages/",
        {"text": "Draft", "scheduled_for": delivery.isoformat()},
        format="json",
    )
    url = f"/api/v1/scheduled-messages/{scheduled.data['id']}/"

    updated = authenticated(alice).patch(
        url,
        {
            "text": "Final",
            "scheduled_for": (delivery + timedelta(hours=1)).isoformat(),
        },
        format="json",
    )
    cancelled = authenticated(alice).delete(url)

    assert updated.status_code == 200
    assert updated.data["text"] == "Final"
    assert cancelled.status_code == 204
    assert Message.objects.get(pk=scheduled.data["id"]).status == "CANCELLED"
