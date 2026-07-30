from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class EchoUserAdmin(UserAdmin):
    list_display = ("username", "email", "is_active", "date_joined")
    list_filter = ("is_active", "is_staff", "group_invite_policy")
    search_fields = ("username", "email")
    ordering = ("username",)
    fieldsets = UserAdmin.fieldsets + (
        (
            "EchoMessenger profile",
            {"fields": ("avatar", "bio", "group_invite_policy")},
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "EchoMessenger profile",
            {"fields": ("email", "avatar", "bio", "group_invite_policy")},
        ),
    )
