from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.accounts.serializers import UserPublicSerializer

from .models import ChatSpace, Role, SpaceMembership, Topic
from .services import effective_permissions

User = get_user_model()


def validate_image(value, *, field_name="avatar"):
    if value is None:
        return value
    if value.size > 5 * 1024 * 1024:
        raise serializers.ValidationError(
            f"The {field_name} must be 5 MiB or smaller."
        )
    content_type = getattr(value, "content_type", "")
    if content_type and not content_type.startswith("image/"):
        raise serializers.ValidationError(f"The {field_name} must be an image.")
    return value


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = (
            "id",
            "name",
            "can_send_messages",
            "can_send_media",
            "can_manage_topics",
            "can_manage_members",
            "can_delete_messages",
            "can_manage_roles",
            "can_manage_space",
            "is_default",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "is_default", "created_at", "updated_at")


class SpaceMembershipSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)
    role = RoleSerializer(read_only=True)

    class Meta:
        model = SpaceMembership
        fields = ("id", "user", "role", "joined_at")
        read_only_fields = fields


class TopicSerializer(serializers.ModelSerializer):
    created_by = UserPublicSerializer(read_only=True)

    class Meta:
        model = Topic
        fields = ("id", "space", "name", "created_by", "created_at", "updated_at")
        read_only_fields = ("id", "space", "created_by", "created_at", "updated_at")

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("A topic name is required.")
        space = self.context.get("space") or self.instance.space
        query = Topic.objects.filter(space=space, name__iexact=value)
        if self.instance:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise serializers.ValidationError(
                "A topic with this name already exists."
            )
        return value


class ChatSpaceSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    created_by = UserPublicSerializer(read_only=True)
    membership_count = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()
    my_permissions = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = ChatSpace
        fields = (
            "id",
            "name",
            "display_name",
            "type",
            "avatar_url",
            "created_by",
            "membership_count",
            "my_role",
            "my_permissions",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def _request_user(self):
        request = self.context.get("request")
        return request.user if request else None

    def get_avatar_url(self, space):
        if not space.avatar:
            return None
        request = self.context.get("request")
        url = space.avatar.url
        return request.build_absolute_uri(url) if request else url

    def get_membership_count(self, space):
        return space.memberships.count()

    def get_my_role(self, space):
        user = self._request_user()
        if not user or not user.is_authenticated:
            return None
        membership = next(
            (
                item
                for item in space.memberships.all()
                if item.user_id == user.pk
            ),
            None,
        )
        if membership and membership.role:
            return RoleSerializer(membership.role).data
        return None

    def get_my_permissions(self, space):
        user = self._request_user()
        if space.type == ChatSpace.Type.CHANNEL:
            return effective_permissions(user, space)
        is_member = bool(
            user
            and user.is_authenticated
            and any(
                item.user_id == user.pk
                for item in space.memberships.all()
            )
        )
        return {
            "can_send_messages": is_member,
            "can_send_media": is_member,
            "can_manage_topics": False,
            "can_manage_members": (
                is_member and space.type == ChatSpace.Type.GROUP
            ),
            "can_delete_messages": (
                is_member and space.type == ChatSpace.Type.GROUP
            ),
            "can_manage_roles": False,
            "can_manage_space": (
                is_member and space.type == ChatSpace.Type.GROUP
            ),
        }

    def get_display_name(self, space):
        if space.type != ChatSpace.Type.DIRECT:
            return space.name
        user = self._request_user()
        other = next(
            (
                membership.user
                for membership in space.memberships.all()
                if not user or membership.user_id != user.pk
            ),
            None,
        )
        return other.username if other else "Direct chat"


class SpaceCreateSerializer(serializers.Serializer):
    type = serializers.ChoiceField(
        choices=(ChatSpace.Type.GROUP, ChatSpace.Type.CHANNEL)
    )
    name = serializers.CharField(max_length=100)
    avatar = serializers.ImageField(required=False, allow_null=True)
    member_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        max_length=200,
    )

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("A name is required.")
        return value

    def validate_avatar(self, value):
        return validate_image(value)


class SpaceUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatSpace
        fields = ("name", "avatar")
        extra_kwargs = {
            "name": {"required": False},
            "avatar": {"required": False, "allow_null": True},
        }

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("A name is required.")
        return value

    def validate_avatar(self, value):
        return validate_image(value)

    def update(self, instance, validated_data):
        if "avatar" in validated_data and validated_data["avatar"] is None:
            instance.avatar.delete(save=False)
            validated_data["avatar"] = ""
        return super().update(instance, validated_data)


class DirectSpaceCreateSerializer(serializers.Serializer):
    user_id = serializers.PrimaryKeyRelatedField(
        source="user",
        queryset=User.objects.filter(is_active=True),
    )


class MemberAddSerializer(serializers.Serializer):
    user_id = serializers.PrimaryKeyRelatedField(
        source="user",
        queryset=User.objects.filter(is_active=True),
    )
    role_id = serializers.PrimaryKeyRelatedField(
        source="role",
        queryset=Role.objects.all(),
        required=False,
        allow_null=True,
    )


class MemberRoleUpdateSerializer(serializers.Serializer):
    role_id = serializers.PrimaryKeyRelatedField(
        source="role",
        queryset=Role.objects.all(),
        allow_null=False,
    )
