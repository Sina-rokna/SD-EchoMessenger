from rest_framework.permissions import BasePermission

from .models import ChatSpace, SpaceMembership
from .services import (
    can_manage_members,
    can_manage_roles,
    can_manage_space,
    can_manage_topics,
)


def space_from_object(obj):
    if isinstance(obj, ChatSpace):
        return obj
    return getattr(obj, "space", None)


class IsSpaceMember(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        space = space_from_object(obj)
        return bool(
            space
            and SpaceMembership.objects.filter(
                space=space,
                user=request.user,
            ).exists()
        )


class CanManageSpace(IsSpaceMember):
    def has_object_permission(self, request, view, obj):
        space = space_from_object(obj)
        return bool(space and can_manage_space(request.user, space))


class CanManageMembers(IsSpaceMember):
    def has_object_permission(self, request, view, obj):
        space = space_from_object(obj)
        return bool(space and can_manage_members(request.user, space))


class CanManageTopics(IsSpaceMember):
    def has_object_permission(self, request, view, obj):
        space = space_from_object(obj)
        return bool(space and can_manage_topics(request.user, space))


class CanManageRoles(IsSpaceMember):
    def has_object_permission(self, request, view, obj):
        space = space_from_object(obj)
        return bool(space and can_manage_roles(request.user, space))
