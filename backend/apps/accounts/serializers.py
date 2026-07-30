from django.contrib.auth import get_user_model, password_validation
from django.db.models import Q
from rest_framework import serializers

User = get_user_model()


class UserPublicSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "avatar_url", "bio")
        read_only_fields = fields

    def get_avatar_url(self, user):
        if not user.avatar:
            return None
        request = self.context.get("request")
        url = user.avatar.url
        return request.build_absolute_uri(url) if request else url


class UserPrivateSerializer(UserPublicSerializer):
    class Meta(UserPublicSerializer.Meta):
        fields = UserPublicSerializer.Meta.fields + (
            "email",
            "group_invite_policy",
            "date_joined",
        )
        read_only_fields = fields


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = ("username", "email", "password")

    def validate_username(self, value):
        value = value.strip()
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already in use.")
        return value

    def validate_email(self, value):
        value = User.objects.normalize_email(value).lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email address is already in use.")
        return value

    def validate_password(self, value):
        candidate = User(
            username=self.initial_data.get("username", ""),
            email=self.initial_data.get("email", ""),
        )
        password_validation.validate_password(value, candidate)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        trim_whitespace=False,
        style={"input_type": "password"},
    )


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("username", "email", "avatar", "bio", "group_invite_policy")
        extra_kwargs = {
            "username": {"required": False},
            "email": {"required": False},
            "avatar": {"required": False, "allow_null": True},
        }

    def validate_username(self, value):
        value = value.strip()
        query = User.objects.filter(username__iexact=value).exclude(pk=self.instance.pk)
        if query.exists():
            raise serializers.ValidationError("This username is already in use.")
        return value

    def validate_email(self, value):
        value = User.objects.normalize_email(value).lower()
        query = User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk)
        if query.exists():
            raise serializers.ValidationError("This email address is already in use.")
        return value

    def validate_avatar(self, value):
        if value is None:
            return value
        max_size = 5 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("The avatar must be 5 MiB or smaller.")
        content_type = getattr(value, "content_type", "")
        if content_type and not content_type.startswith("image/"):
            raise serializers.ValidationError("The avatar must be an image.")
        return value

    def update(self, instance, validated_data):
        if "avatar" in validated_data and validated_data["avatar"] is None:
            instance.avatar.delete(save=False)
            validated_data["avatar"] = ""
        return super().update(instance, validated_data)


class UserSearchSerializer(UserPublicSerializer):
    """A named serializer keeps the search response intentionally public."""


def find_login_user(email: str):
    """Resolve an email without leaking whether letter casing differs."""
    return User.objects.filter(
        Q(email__iexact=email),
        is_active=True,
    ).first()
