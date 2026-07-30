import uuid
from pathlib import Path

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models.functions import Lower


def avatar_upload_path(instance: "User", filename: str) -> str:
    """Return a non-guessable storage name while retaining a safe extension."""
    suffix = Path(filename).suffix.lower()[:10]
    return f"avatars/{instance.pk}/{uuid.uuid4().hex}{suffix}"


class EchoUserManager(UserManager):
    """Keep email normalization consistent for command-line and API users."""

    def _create_user(self, username, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email).lower()
        return super()._create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    class GroupInvitePolicy(models.TextChoices):
        EVERYONE = "EVERYONE", "Everyone"
        NOBODY = "NOBODY", "Nobody"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_column="user_id",
    )
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=254, unique=True)
    avatar = models.ImageField(upload_to=avatar_upload_path, blank=True)
    bio = models.CharField(max_length=500, blank=True)
    group_invite_policy = models.CharField(
        max_length=16,
        choices=GroupInvitePolicy.choices,
        default=GroupInvitePolicy.EVERYONE,
    )

    objects = EchoUserManager()

    class Meta:
        ordering = ("username",)
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_email_case_insensitive_unique",
            ),
            models.UniqueConstraint(
                Lower("username"),
                name="accounts_user_username_case_insensitive_unique",
            ),
        ]

    def save(self, *args, **kwargs):
        self.email = self.__class__.objects.normalize_email(self.email).lower()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.username
