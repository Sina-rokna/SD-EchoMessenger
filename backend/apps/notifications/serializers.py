from rest_framework import serializers

from apps.accounts.serializers import UserPublicSerializer

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    actor = UserPublicSerializer(read_only=True)
    space_id = serializers.UUIDField(read_only=True, allow_null=True)
    message_id = serializers.UUIDField(read_only=True, allow_null=True)
    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "event_type",
            "actor",
            "space_id",
            "message_id",
            "is_read",
            "read_at",
            "created_at",
        )
        read_only_fields = fields
