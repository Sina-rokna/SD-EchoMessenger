from django.contrib import admin

from .models import Attachment, Message


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0
    readonly_fields = (
        "original_name",
        "content_type",
        "size",
        "category",
        "created_at",
    )


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "space", "status", "sent_at", "scheduled_for")
    list_filter = ("status", "space__type")
    search_fields = ("text", "sender__username", "space__name")
    autocomplete_fields = ("sender", "space", "topic")
    readonly_fields = ("created_at", "sent_at", "edited_at")
    inlines = (AttachmentInline,)


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("original_name", "message", "category", "size", "created_at")
    list_filter = ("category",)
    search_fields = ("original_name", "message__text")
    readonly_fields = ("created_at",)
