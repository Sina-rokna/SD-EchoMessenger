from django.contrib import admin

from .models import ChatSpace, Role, SpaceMembership, Topic


class MembershipInline(admin.TabularInline):
    model = SpaceMembership
    extra = 0
    autocomplete_fields = ("user", "role")


class TopicInline(admin.TabularInline):
    model = Topic
    extra = 0


@admin.register(ChatSpace)
class ChatSpaceAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "created_by", "created_at", "updated_at")
    list_filter = ("type",)
    search_fields = ("name", "created_by__username", "created_by__email")
    autocomplete_fields = ("created_by",)
    readonly_fields = ("direct_key", "created_at", "updated_at")
    inlines = (MembershipInline, TopicInline)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "space", "is_default", "updated_at")
    list_filter = ("is_default",)
    search_fields = ("name", "space__name")


@admin.register(SpaceMembership)
class SpaceMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "space", "role", "joined_at")
    search_fields = ("user__username", "space__name", "role__name")
    autocomplete_fields = ("user", "space", "role")


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "space", "created_by", "created_at")
    search_fields = ("name", "space__name")
    autocomplete_fields = ("space", "created_by")
