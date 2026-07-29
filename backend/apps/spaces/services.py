from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from .models import ChatSpace, Role, SpaceMembership

if TYPE_CHECKING:
    from apps.messaging.models import Message

User = get_user_model()

ALL_CHANNEL_PERMISSIONS = {
    field: True for field in Role.PERMISSION_FIELDS
}


def membership_for(user, space: ChatSpace) -> SpaceMembership | None:
    if not user or not user.is_authenticated:
        return None
    return (
        SpaceMembership.objects.select_related("role")
        .filter(user=user, space=space)
        .first()
    )


def is_member(user, space: ChatSpace) -> bool:
    return membership_for(user, space) is not None


def is_owner(user, space: ChatSpace) -> bool:
    return bool(user and user.is_authenticated and space.created_by_id == user.pk)


def effective_permissions(user, space: ChatSpace) -> dict[str, bool]:
    """Return the actor's channel permissions; owners always have all of them."""
    if space.type != ChatSpace.Type.CHANNEL:
        return {field: False for field in Role.PERMISSION_FIELDS}
    if is_owner(user, space):
        return dict(ALL_CHANNEL_PERMISSIONS)
    membership = membership_for(user, space)
    if not membership or not membership.role:
        return {field: False for field in Role.PERMISSION_FIELDS}
    return membership.role.permission_map()


def can_send_messages(user, space: ChatSpace, *, has_attachments=False) -> bool:
    membership = membership_for(user, space)
    if not membership:
        return False
    if space.type in (ChatSpace.Type.DIRECT, ChatSpace.Type.GROUP):
        return True
    permissions = effective_permissions(user, space)
    if not permissions["can_send_messages"]:
        return False
    return not has_attachments or permissions["can_send_media"]


def can_delete_message(user, message: "Message") -> bool:
    if not user or not user.is_authenticated:
        return False
    if message.sender_id == user.pk:
        return True
    space = message.space
    if space.type == ChatSpace.Type.GROUP:
        return is_member(user, space)
    if space.type == ChatSpace.Type.CHANNEL:
        return effective_permissions(user, space)["can_delete_messages"]
    return False


def can_manage_space(user, space: ChatSpace) -> bool:
    if space.type == ChatSpace.Type.GROUP:
        return is_member(user, space)
    if space.type == ChatSpace.Type.CHANNEL:
        return effective_permissions(user, space)["can_manage_space"]
    return False


def can_manage_members(user, space: ChatSpace) -> bool:
    if space.type == ChatSpace.Type.GROUP:
        return is_member(user, space)
    if space.type == ChatSpace.Type.CHANNEL:
        return effective_permissions(user, space)["can_manage_members"]
    return False


def can_manage_topics(user, space: ChatSpace) -> bool:
    return bool(
        space.type == ChatSpace.Type.CHANNEL
        and effective_permissions(user, space)["can_manage_topics"]
    )


def can_manage_roles(user, space: ChatSpace) -> bool:
    return bool(
        space.type == ChatSpace.Type.CHANNEL
        and effective_permissions(user, space)["can_manage_roles"]
    )


def canonical_direct_key(first_user_id, second_user_id) -> str:
    if first_user_id == second_user_id:
        raise ValidationError({"user_id": "You cannot chat directly with yourself."})
    return ":".join(sorted((str(first_user_id), str(second_user_id))))


@transaction.atomic
def get_or_create_direct_space(actor, other_user):
    key = canonical_direct_key(actor.pk, other_user.pk)
    existing = (
        ChatSpace.objects.select_for_update()
        .filter(direct_key=key, type=ChatSpace.Type.DIRECT)
        .first()
    )
    if existing:
        return existing, False

    try:
        # The savepoint keeps the outer transaction usable if a concurrent
        # request wins the unique-key race.
        with transaction.atomic():
            space = ChatSpace.objects.create(
                type=ChatSpace.Type.DIRECT,
                created_by=actor,
                direct_key=key,
            )
    except IntegrityError:
        # A concurrent transaction may have created the same canonical pair.
        space = ChatSpace.objects.get(
            direct_key=key,
            type=ChatSpace.Type.DIRECT,
        )
        return space, False

    SpaceMembership.objects.bulk_create(
        (
            SpaceMembership(space=space, user=actor),
            SpaceMembership(space=space, user=other_user),
        )
    )
    _schedule_user_event(
        other_user.pk,
        "member.updated",
        {
            "space_id": str(space.pk),
            "user_id": str(other_user.pk),
            "action": "added",
            "role_id": None,
        },
    )
    return space, True


def _default_channel_role(space: ChatSpace) -> Role:
    role = space.roles.filter(is_default=True).first()
    if role:
        return role
    return Role.objects.create(
        space=space,
        name="Member",
        is_default=True,
        can_send_messages=True,
        can_send_media=True,
    )


def _resolve_users(user_ids: Iterable) -> list:
    unique_ids = set(user_ids)
    users = list(User.objects.filter(pk__in=unique_ids, is_active=True))
    if len(users) != len(unique_ids):
        raise ValidationError({"member_ids": "One or more users do not exist."})
    return users


def _check_group_invite_policy(actor, users):
    blocked = [
        user.username
        for user in users
        if user.pk != actor.pk
        and user.group_invite_policy == User.GroupInvitePolicy.NOBODY
    ]
    if blocked:
        raise ValidationError(
            {
                "member_ids": (
                    "These users do not allow group invitations: "
                    + ", ".join(sorted(blocked))
                )
            }
        )


@transaction.atomic
def create_space(*, actor, space_type: str, name: str, avatar=None, member_ids=()):
    if space_type not in (ChatSpace.Type.GROUP, ChatSpace.Type.CHANNEL):
        raise ValidationError({"type": "Use the direct-chat endpoint for DIRECT."})
    users = _resolve_users(member_ids)
    if space_type == ChatSpace.Type.GROUP:
        has_invitee = any(user.pk != actor.pk for user in users)
        if not has_invitee:
            raise ValidationError(
                {"member_ids": "A group needs at least one other member."}
            )
        _check_group_invite_policy(actor, users)

    space = ChatSpace(
        type=space_type,
        name=name.strip(),
        created_by=actor,
    )
    if avatar is not None:
        space.avatar = avatar
    space.full_clean(exclude=("members",))
    space.save()

    default_role = (
        _default_channel_role(space)
        if space_type == ChatSpace.Type.CHANNEL
        else None
    )
    members_by_id = {user.pk: user for user in users}
    members_by_id[actor.pk] = actor
    SpaceMembership.objects.bulk_create(
        SpaceMembership(
            space=space,
            user=user,
            role=default_role,
        )
        for user in members_by_id.values()
    )
    for user in members_by_id.values():
        if user.pk == actor.pk:
            continue
        payload = {
            "space_id": str(space.pk),
            "user_id": str(user.pk),
            "action": "added",
            "role_id": str(default_role.pk) if default_role else None,
        }
        _schedule_user_event(user.pk, "member.updated", payload)
        _create_membership_notification(
            recipient=user,
            actor=actor,
            space=space,
        )
    return space


def require_member(user, space: ChatSpace) -> SpaceMembership:
    membership = membership_for(user, space)
    if not membership:
        raise NotFound("Chat space not found.")
    return membership


def _schedule_space_event(space: ChatSpace, event_type: str, payload: dict):
    space_id = str(space.pk)

    def publish():
        from apps.messaging.realtime import broadcast_space_event

        broadcast_space_event(space_id, event_type, payload)

    transaction.on_commit(publish)


def _schedule_user_event(user_id, event_type: str, payload: dict):
    def publish():
        from apps.messaging.realtime import broadcast_user_event

        broadcast_user_event(str(user_id), event_type, payload)

    transaction.on_commit(publish)


@transaction.atomic
def add_member(*, actor, space: ChatSpace, user, role: Role | None = None):
    require_member(actor, space)
    if not can_manage_members(actor, space):
        raise PermissionDenied("You cannot add members to this space.")
    if space.type == ChatSpace.Type.DIRECT:
        raise ValidationError("Direct chats always have exactly two members.")
    if (
        space.type == ChatSpace.Type.GROUP
        and user.pk != actor.pk
        and user.group_invite_policy == User.GroupInvitePolicy.NOBODY
    ):
        raise ValidationError(
            {"user_id": "This user does not allow group invitations."}
        )
    if SpaceMembership.objects.filter(space=space, user=user).exists():
        raise ValidationError({"user_id": "This user is already a member."})

    if space.type == ChatSpace.Type.CHANNEL:
        role = role or _default_channel_role(space)
        validate_assignable_role(actor=actor, space=space, role=role)
    elif role is not None:
        raise ValidationError({"role_id": "Groups do not use channel roles."})

    membership = SpaceMembership.objects.create(
        space=space,
        user=user,
        role=role,
    )
    payload = {
        "space_id": str(space.pk),
        "user_id": str(user.pk),
        "action": "added",
        "role_id": str(role.pk) if role else None,
    }
    _schedule_space_event(space, "member.updated", payload)
    _schedule_user_event(user.pk, "member.updated", payload)
    _create_membership_notification(
        recipient=user,
        actor=actor,
        space=space,
    )
    return membership


def _create_membership_notification(*, recipient, actor, space):
    from apps.notifications.services import create_notification

    create_notification(
        recipient=recipient,
        actor=actor,
        event_type="MEMBER_ADDED",
        space=space,
    )


def validate_assignable_role(*, actor, space: ChatSpace, role: Role):
    if role.space_id != space.pk:
        raise ValidationError({"role_id": "The role belongs to another channel."})
    actor_permissions = effective_permissions(actor, space)
    forbidden = [
        field
        for field, enabled in role.permission_map().items()
        if enabled and not actor_permissions[field]
    ]
    if forbidden:
        raise PermissionDenied(
            "You cannot grant permissions that you do not have."
        )


@transaction.atomic
def assign_role(*, actor, membership: SpaceMembership, role: Role):
    space = membership.space
    if not can_manage_roles(actor, space):
        raise PermissionDenied("You cannot assign channel roles.")
    if membership.user_id == space.created_by_id:
        raise ValidationError("The channel owner does not need an assigned role.")
    validate_assignable_role(actor=actor, space=space, role=role)
    membership.role = role
    membership.full_clean()
    membership.save(update_fields=("role",))
    payload = {
        "space_id": str(space.pk),
        "user_id": str(membership.user_id),
        "action": "role_changed",
        "role_id": str(role.pk),
    }
    _schedule_space_event(space, "member.updated", payload)
    _schedule_user_event(membership.user_id, "member.updated", payload)
    return membership


@transaction.atomic
def remove_member(*, actor, membership: SpaceMembership, self_leave=False):
    space = membership.space
    if space.type == ChatSpace.Type.DIRECT:
        raise ValidationError("Members cannot be removed from a direct chat.")
    if self_leave:
        if actor.pk != membership.user_id:
            raise PermissionDenied("You can only leave as yourself.")
    elif not can_manage_members(actor, space):
        raise PermissionDenied("You cannot remove members from this space.")

    is_channel_owner = (
        space.type == ChatSpace.Type.CHANNEL
        and membership.user_id == space.created_by_id
    )
    if is_channel_owner:
        raise ValidationError("The channel owner cannot leave or be removed.")

    removed_user_id = membership.user_id
    membership.delete()

    if (
        space.type == ChatSpace.Type.GROUP
        and removed_user_id == space.created_by_id
    ):
        replacement = (
            space.memberships.select_related("user")
            .order_by("joined_at")
            .first()
        )
        if replacement:
            space.created_by = replacement.user
            space.save(update_fields=("created_by", "updated_at"))
        else:
            space.delete()
            return

    payload = {
        "space_id": str(space.pk),
        "user_id": str(removed_user_id),
        "action": "left" if self_leave else "removed",
        "role_id": None,
    }
    _schedule_space_event(space, "member.updated", payload)
    _schedule_user_event(removed_user_id, "member.updated", payload)


def validate_role_permissions(actor, space: ChatSpace, attrs: dict):
    actor_permissions = effective_permissions(actor, space)
    forbidden = [
        field
        for field in Role.PERMISSION_FIELDS
        if attrs.get(field) is True and not actor_permissions[field]
    ]
    if forbidden:
        raise PermissionDenied(
            "You cannot enable permissions that you do not have."
        )


def visible_spaces_for(user) -> QuerySet[ChatSpace]:
    return (
        ChatSpace.objects.filter(memberships__user=user)
        .select_related("created_by")
        .prefetch_related("memberships__user", "memberships__role")
        .distinct()
    )
