import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.notifications.models import Notification
from apps.notifications.services import create_notification

User = get_user_model()


def authenticated(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.mark.django_db
def test_notification_list_and_single_read_are_recipient_scoped():
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
    notification = create_notification(
        recipient=bob,
        actor=alice,
        event_type=Notification.EventType.MEMBER_ADDED,
    )

    listed = authenticated(bob).get("/api/v1/notifications/")
    forbidden = authenticated(alice).post(
        f"/api/v1/notifications/{notification.pk}/read/"
    )
    marked = authenticated(bob).post(
        f"/api/v1/notifications/{notification.pk}/read/"
    )

    assert [item["id"] for item in listed.data["results"]] == [
        str(notification.pk)
    ]
    assert forbidden.status_code == 404
    assert marked.status_code == 200
    assert marked.data["is_read"] is True


@pytest.mark.django_db
def test_read_all_only_updates_current_users_notifications():
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
    alice_notification = create_notification(
        recipient=alice,
        actor=bob,
        event_type=Notification.EventType.MEMBER_ADDED,
    )
    bob_notification = create_notification(
        recipient=bob,
        actor=alice,
        event_type=Notification.EventType.MEMBER_ADDED,
    )

    response = authenticated(alice).post("/api/v1/notifications/read-all/")

    alice_notification.refresh_from_db()
    bob_notification.refresh_from_db()
    assert response.status_code == 200
    assert response.data["updated"] == 1
    assert alice_notification.is_read
    assert not bob_notification.is_read
