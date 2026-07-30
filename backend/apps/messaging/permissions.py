from rest_framework.permissions import BasePermission

from apps.spaces.services import can_delete_message, is_member


class CanReadMessage(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, message):
        return is_member(request.user, message.space)


class IsMessageAuthor(CanReadMessage):
    def has_object_permission(self, request, view, message):
        return bool(
            super().has_object_permission(request, view, message)
            and message.sender_id == request.user.pk
        )


class CanDeleteMessage(CanReadMessage):
    def has_object_permission(self, request, view, message):
        return bool(
            super().has_object_permission(request, view, message)
            and can_delete_message(request.user, message)
        )
