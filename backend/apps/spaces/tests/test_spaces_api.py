from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework.test import APIClient

from apps.notifications.models import Notification
from apps.spaces.models import ChatSpace, Role, SpaceMembership
from apps.spaces.services import (
    canonical_direct_key,
    create_space,
    get_or_create_direct_space,
)

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


@pytest.mark.django_db
def test_direct_chat_is_canonical_and_has_exactly_two_members(users):
    alice, bob, _ = users

    first = authenticated(alice).post(
        "/api/v1/spaces/direct/",
        {"user_id": str(bob.pk)},
        format="json",
    )
    second = authenticated(bob).post(
        "/api/v1/spaces/direct/",
        {"user_id": str(alice.pk)},
        format="json",
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.data["id"] == second.data["id"]
    space = ChatSpace.objects.get(pk=first.data["id"])
    assert space.type == ChatSpace.Type.DIRECT
    assert space.memberships.count() == 2
    assert ChatSpace.objects.filter(type=ChatSpace.Type.DIRECT).count() == 1


@pytest.mark.django_db
def test_cannot_open_direct_chat_with_self(users):
    alice, _, _ = users
    response = authenticated(alice).post(
        "/api/v1/spaces/direct/",
        {"user_id": str(alice.pk)},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_group_creation_respects_invite_policy(users):
    alice, bob, _ = users
    bob.group_invite_policy = User.GroupInvitePolicy.NOBODY
    bob.save(update_fields=("group_invite_policy",))

    response = authenticated(alice).post(
        "/api/v1/spaces/",
        {
            "type": "GROUP",
            "name": "Private study group",
            "member_ids": [str(bob.pk)],
        },
        format="json",
    )

    assert response.status_code == 400
    assert ChatSpace.objects.filter(type=ChatSpace.Type.GROUP).count() == 0


@pytest.mark.django_db
def test_group_requires_at_least_one_other_member(users):
    alice, _, _ = users

    missing_members = authenticated(alice).post(
        "/api/v1/spaces/",
        {"type": "GROUP", "name": "Only me", "member_ids": []},
        format="json",
    )
    actor_only = authenticated(alice).post(
        "/api/v1/spaces/",
        {
            "type": "GROUP",
            "name": "Still only me",
            "member_ids": [str(alice.pk)],
        },
        format="json",
    )

    assert missing_members.status_code == 400
    assert actor_only.status_code == 400
    assert not ChatSpace.objects.filter(type=ChatSpace.Type.GROUP).exists()


@pytest.mark.django_db
def test_any_group_member_can_edit_and_delete_group(users):
    alice, bob, _ = users
    created = authenticated(alice).post(
        "/api/v1/spaces/",
        {
            "type": "GROUP",
            "name": "Original name",
            "member_ids": [str(bob.pk)],
        },
        format="json",
    )
    space_id = created.data["id"]

    changed = authenticated(bob).patch(
        f"/api/v1/spaces/{space_id}/",
        {"name": "Renamed by Bob"},
        format="json",
    )
    deleted = authenticated(bob).delete(f"/api/v1/spaces/{space_id}/")

    assert changed.status_code == 200
    assert changed.data["name"] == "Renamed by Bob"
    assert deleted.status_code == 204
    assert not ChatSpace.objects.filter(pk=space_id).exists()


@pytest.mark.django_db
def test_nonmember_cannot_discover_space(users):
    alice, bob, carol = users
    created = authenticated(alice).post(
        "/api/v1/spaces/",
        {
            "type": "GROUP",
            "name": "Hidden",
            "member_ids": [str(bob.pk)],
        },
        format="json",
    )

    response = authenticated(carol).get(
        f"/api/v1/spaces/{created.data['id']}/"
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_channel_has_default_role_and_owner_can_create_topic(users):
    alice, bob, _ = users
    created = authenticated(alice).post(
        "/api/v1/spaces/",
        {
            "type": "CHANNEL",
            "name": "Engineering",
            "member_ids": [str(bob.pk)],
        },
        format="json",
    )
    space = ChatSpace.objects.get(pk=created.data["id"])

    topic = authenticated(alice).post(
        f"/api/v1/spaces/{space.pk}/topics/",
        {"name": "Backend"},
        format="json",
    )
    denied = authenticated(bob).post(
        f"/api/v1/spaces/{space.pk}/topics/",
        {"name": "Unauthorized"},
        format="json",
    )

    assert Role.objects.filter(space=space, is_default=True).count() == 1
    assert SpaceMembership.objects.get(space=space, user=bob).role.is_default
    assert topic.status_code == 201
    assert denied.status_code == 403


@pytest.mark.django_db
def test_channel_role_manager_cannot_escalate_privileges(users):
    alice, bob, _ = users
    created = authenticated(alice).post(
        "/api/v1/spaces/",
        {
            "type": "CHANNEL",
            "name": "Engineering",
            "member_ids": [str(bob.pk)],
        },
        format="json",
    )
    space_id = created.data["id"]
    manager_role = authenticated(alice).post(
        f"/api/v1/spaces/{space_id}/roles/",
        {
            "name": "Role manager",
            "can_send_messages": True,
            "can_send_media": False,
            "can_manage_roles": True,
        },
        format="json",
    )
    assert manager_role.status_code == 201
    assigned = authenticated(alice).patch(
        f"/api/v1/spaces/{space_id}/members/{bob.pk}/",
        {"role_id": manager_role.data["id"]},
        format="json",
    )
    assert assigned.status_code == 200

    escalated = authenticated(bob).post(
        f"/api/v1/spaces/{space_id}/roles/",
        {
            "name": "Hidden owner",
            "can_send_messages": True,
            "can_manage_roles": True,
            "can_manage_space": True,
        },
        format="json",
    )

    assert escalated.status_code == 403
    assert not Role.objects.filter(space_id=space_id, name="Hidden owner").exists()


@pytest.mark.django_db
def test_role_from_another_channel_cannot_be_assigned(users):
    alice, bob, _ = users
    first = authenticated(alice).post(
        "/api/v1/spaces/",
        {
            "type": "CHANNEL",
            "name": "First",
            "member_ids": [str(bob.pk)],
        },
        format="json",
    )
    second = authenticated(alice).post(
        "/api/v1/spaces/",
        {"type": "CHANNEL", "name": "Second"},
        format="json",
    )
    foreign_role = Role.objects.get(
        space_id=second.data["id"],
        is_default=True,
    )

    response = authenticated(alice).patch(
        f"/api/v1/spaces/{first.data['id']}/members/{bob.pk}/",
        {"role_id": str(foreign_role.pk)},
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_channel_owner_cannot_leave(users):
    alice, _, _ = users
    created = authenticated(alice).post(
        "/api/v1/spaces/",
        {"type": "CHANNEL", "name": "Engineering"},
        format="json",
    )

    response = authenticated(alice).delete(
        f"/api/v1/spaces/{created.data['id']}/members/me/"
    )

    assert response.status_code == 400


@pytest.mark.parametrize(
    "space_type",
    (ChatSpace.Type.GROUP, ChatSpace.Type.CHANNEL),
)
@pytest.mark.django_db(transaction=True)
def test_initial_invitee_gets_persistent_and_live_membership_event(space_type):
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

    with patch(
        "apps.messaging.realtime.broadcast_user_event"
    ) as broadcast_user_event:
        space = create_space(
            actor=alice,
            space_type=space_type,
            name=f"Demo {space_type}",
            member_ids=[bob.pk],
        )

    member_calls = [
        call.args
        for call in broadcast_user_event.call_args_list
        if call.args[1] == "member.updated"
    ]
    assert member_calls == [
        (
            str(bob.pk),
            "member.updated",
            {
                "space_id": str(space.pk),
                "user_id": str(bob.pk),
                "action": "added",
                "role_id": (
                    str(space.roles.get(is_default=True).pk)
                    if space_type == ChatSpace.Type.CHANNEL
                    else None
                ),
            },
        )
    ]
    assert Notification.objects.filter(
        recipient=bob,
        actor=alice,
        space=space,
        event_type=Notification.EventType.MEMBER_ADDED,
    ).exists()


@pytest.mark.django_db(transaction=True)
def test_direct_invitee_gets_live_space_visibility_event_without_notification():
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

    with patch(
        "apps.messaging.realtime.broadcast_user_event"
    ) as broadcast_user_event:
        space, created = get_or_create_direct_space(alice, bob)

    assert created is True
    broadcast_user_event.assert_called_once_with(
        str(bob.pk),
        "member.updated",
        {
            "space_id": str(space.pk),
            "user_id": str(bob.pk),
            "action": "added",
            "role_id": None,
        },
    )
    assert not Notification.objects.filter(
        recipient=bob,
        space=space,
        event_type=Notification.EventType.MEMBER_ADDED,
    ).exists()


@pytest.mark.django_db(transaction=True)
def test_space_delete_broadcast_freezes_id_before_model_is_deleted():
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
    space = create_space(
        actor=alice,
        space_type=ChatSpace.Type.GROUP,
        name="Temporary",
        member_ids=[bob.pk],
    )
    space_id = str(space.pk)

    with (
        patch(
            "apps.messaging.realtime.broadcast_space_event"
        ) as broadcast_space_event,
        patch(
            "apps.messaging.realtime.broadcast_user_event"
        ) as broadcast_user_event,
    ):
        response = authenticated(alice).delete(f"/api/v1/spaces/{space_id}/")

    assert response.status_code == 204
    broadcast_space_event.assert_called_once_with(
        space_id,
        "space.updated",
        {"space_id": space_id, "action": "deleted"},
    )
    broadcast_user_event.assert_called_once_with(
        str(bob.pk),
        "member.updated",
        {
            "space_id": space_id,
            "user_id": str(bob.pk),
            "action": "space_deleted",
            "role_id": None,
        },
    )


@pytest.mark.django_db(transaction=True)
def test_direct_create_unique_race_recovers_after_inner_savepoint():
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
    existing = ChatSpace.objects.create(
        type=ChatSpace.Type.DIRECT,
        created_by=alice,
        direct_key=canonical_direct_key(alice.pk, bob.pk),
    )
    SpaceMembership.objects.bulk_create(
        (
            SpaceMembership(space=existing, user=alice),
            SpaceMembership(space=existing, user=bob),
        )
    )

    with (
        patch.object(ChatSpace.objects, "select_for_update") as locked,
        patch.object(
            ChatSpace.objects,
            "create",
            side_effect=IntegrityError("simulated concurrent insert"),
        ),
    ):
        locked.return_value.filter.return_value.first.return_value = None
        resolved, created = get_or_create_direct_space(alice, bob)

    assert resolved == existing
    assert created is False
