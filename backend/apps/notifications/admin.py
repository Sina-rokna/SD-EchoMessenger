from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("event_type", "recipient", "actor", "created_at", "read_at")
    list_filter = ("event_type", "read_at")
    search_fields = (
        "recipient__username",
        "actor__username",
        "space__name",
        "message__text",
    )
    autocomplete_fields = ("recipient", "actor", "space", "message")
    readonly_fields = ("created_at",)
