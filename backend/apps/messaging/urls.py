from django.urls import path

from .views import (
    AttachmentDownloadView,
    MessageDetailView,
    MessageSearchView,
    ScheduledMessageDetailView,
    ScheduledMessageListView,
    SpaceMessageListCreateView,
)

urlpatterns = [
    path(
        "spaces/<uuid:space_id>/messages/",
        SpaceMessageListCreateView.as_view(),
        name="space-message-list",
    ),
    path(
        "spaces/<uuid:space_id>/messages/search/",
        MessageSearchView.as_view(),
        name="message-search",
    ),
    path(
        "messages/<uuid:message_id>/",
        MessageDetailView.as_view(),
        name="message-detail",
    ),
    path(
        "scheduled-messages/",
        ScheduledMessageListView.as_view(),
        name="scheduled-message-list",
    ),
    path(
        "scheduled-messages/<uuid:message_id>/",
        ScheduledMessageDetailView.as_view(),
        name="scheduled-message-detail",
    ),
    path(
        "attachments/<uuid:attachment_id>/download/",
        AttachmentDownloadView.as_view(),
        name="attachment-download",
    ),
]
