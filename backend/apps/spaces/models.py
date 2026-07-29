import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def space_avatar_upload_path(instance: "ChatSpace", filename: str) -> str:
    suffix = Path(filename).suffix.lower()[:10]
    return f"space-avatars/{instance.pk}/{uuid.uuid4().hex}{suffix}"


class ChatSpace(models.Model):
    class Type(models.TextChoices):
        DIRECT = "DIRECT", "Direct"
        GROUP = "GROUP", "Group"
        CHANNEL = "CHANNEL", "Channel"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_column="space_id",
    )
    name = models.CharField(max_length=100, blank=True)
    type = models.CharField(max_length=10, choices=Type.choices)
    avatar = models.ImageField(upload_to=space_avatar_upload_path, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_spaces",
    )
    direct_key = models.CharField(
        max_length=73,
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="SpaceMembership",
        related_name="chat_spaces",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(type="DIRECT", direct_key__isnull=False)
                    | models.Q(
                        type__in=("GROUP", "CHANNEL"),
                        direct_key__isnull=True,
                    )
                ),
                name="spaces_direct_key_matches_type",
            ),
        ]
        indexes = [
            models.Index(fields=("type", "updated_at")),
        ]

    def clean(self):
        super().clean()
        if self.type == self.Type.DIRECT:
            if not self.direct_key:
                raise ValidationError({"direct_key": "A direct chat needs a key."})
        else:
            if self.direct_key:
                raise ValidationError(
                    {"direct_key": "Only direct chats may have a direct key."}
                )
            if not self.name.strip():
                raise ValidationError({"name": "Groups and channels need a name."})

    def __str__(self) -> str:
        return self.name or f"Direct chat {self.pk}"


class Role(models.Model):
    """An editable, data-driven collection of channel permissions."""

    PERMISSION_FIELDS = (
        "can_send_messages",
        "can_send_media",
        "can_manage_topics",
        "can_manage_members",
        "can_delete_messages",
        "can_manage_roles",
        "can_manage_space",
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_column="role_id",
    )
    space = models.ForeignKey(
        ChatSpace,
        on_delete=models.CASCADE,
        related_name="roles",
    )
    name = models.CharField(max_length=50)
    can_send_messages = models.BooleanField(default=True)
    can_send_media = models.BooleanField(default=True)
    can_manage_topics = models.BooleanField(default=False)
    can_manage_members = models.BooleanField(default=False)
    can_delete_messages = models.BooleanField(default=False)
    can_manage_roles = models.BooleanField(default=False)
    can_manage_space = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=("space", "name"),
                name="spaces_role_name_unique_per_space",
            ),
            models.UniqueConstraint(
                fields=("space",),
                condition=models.Q(is_default=True),
                name="spaces_one_default_role_per_space",
            ),
        ]

    def clean(self):
        super().clean()
        if self.space_id and self.space.type != ChatSpace.Type.CHANNEL:
            raise ValidationError("Roles can only belong to channels.")

    def permission_map(self) -> dict[str, bool]:
        return {field: bool(getattr(self, field)) for field in self.PERMISSION_FIELDS}

    def __str__(self) -> str:
        return f"{self.space}: {self.name}"


class SpaceMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="space_memberships",
    )
    space = models.ForeignKey(
        ChatSpace,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        related_name="memberships",
        null=True,
        blank=True,
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("joined_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("user", "space"),
                name="spaces_membership_user_space_unique",
            ),
        ]
        indexes = [
            models.Index(fields=("space", "user")),
            models.Index(fields=("user", "space")),
        ]

    def clean(self):
        super().clean()
        if self.role_id:
            if self.space.type != ChatSpace.Type.CHANNEL:
                raise ValidationError({"role": "Only channel members have roles."})
            if self.role.space_id != self.space_id:
                raise ValidationError(
                    {"role": "The role must belong to the same channel."}
                )

    def __str__(self) -> str:
        return f"{self.user} in {self.space}"


class Topic(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_column="topic_id",
    )
    space = models.ForeignKey(
        ChatSpace,
        on_delete=models.CASCADE,
        related_name="topics",
    )
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_topics",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("space", "name"),
                name="spaces_topic_name_unique_per_channel",
            ),
        ]

    def clean(self):
        super().clean()
        if self.space_id and self.space.type != ChatSpace.Type.CHANNEL:
            raise ValidationError("Topics can only belong to channels.")

    def __str__(self) -> str:
        return f"{self.space}: {self.name}"
