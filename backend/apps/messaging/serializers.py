from rest_framework import serializers

from apps.accounts.serializers import UserPublicSerializer
from apps.spaces.models import Topic

from .models import Attachment, Message


class AttachmentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = (
            "id",
            "original_name",
            "content_type",
            "size",
            "category",
            "download_url",
            "created_at",
        )
        read_only_fields = fields

    def get_download_url(self, attachment):
        path = f"/api/v1/attachments/{attachment.pk}/download/"
        request = self.context.get("request")
        return request.build_absolute_uri(path) if request else path


class MessageSerializer(serializers.ModelSerializer):
    sender = UserPublicSerializer(read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    topic_id = serializers.UUIDField(read_only=True, allow_null=True)
    is_edited = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = (
            "id",
            "space",
            "topic_id",
            "sender",
            "text",
            "attachments",
            "status",
            "scheduled_for",
            "sent_at",
            "edited_at",
            "is_edited",
            "failure_reason",
            "client_nonce",
            "created_at",
        )
        read_only_fields = fields

    def get_is_edited(self, message):
        return message.edited_at is not None


class MessageCreateSerializer(serializers.Serializer):
    text = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=False,
        max_length=20_000,
    )
    topic_id = serializers.PrimaryKeyRelatedField(
        source="topic",
        queryset=Topic.objects.all(),
        required=False,
        allow_null=True,
    )
    scheduled_for = serializers.DateTimeField(required=False, allow_null=True)
    client_nonce = serializers.UUIDField(required=False, allow_null=True)


class MessageEditSerializer(serializers.Serializer):
    text = serializers.CharField(
        allow_blank=True,
        trim_whitespace=False,
        max_length=20_000,
    )


class ScheduledMessageUpdateSerializer(serializers.Serializer):
    text = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=False,
        max_length=20_000,
    )
    topic_id = serializers.PrimaryKeyRelatedField(
        source="topic",
        queryset=Topic.objects.all(),
        required=False,
        allow_null=False,
    )
    scheduled_for = serializers.DateTimeField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "Provide at least one field to update."
            )
        return attrs
