from django.urls import path

from .views import (
    DirectSpaceCreateView,
    LeaveSpaceView,
    MemberDetailView,
    MemberListCreateView,
    RoleDetailView,
    RoleListCreateView,
    SpaceDetailView,
    SpaceListCreateView,
    TopicDetailView,
    TopicListCreateView,
)

urlpatterns = [
    path("spaces/", SpaceListCreateView.as_view(), name="space-list"),
    path("spaces/direct/", DirectSpaceCreateView.as_view(), name="direct-space"),
    path(
        "spaces/<uuid:space_id>/",
        SpaceDetailView.as_view(),
        name="space-detail",
    ),
    path(
        "spaces/<uuid:space_id>/members/",
        MemberListCreateView.as_view(),
        name="member-list",
    ),
    path(
        "spaces/<uuid:space_id>/members/me/",
        LeaveSpaceView.as_view(),
        name="space-leave",
    ),
    path(
        "spaces/<uuid:space_id>/members/<uuid:user_id>/",
        MemberDetailView.as_view(),
        name="member-detail",
    ),
    path(
        "spaces/<uuid:space_id>/topics/",
        TopicListCreateView.as_view(),
        name="topic-list",
    ),
    path("topics/<uuid:topic_id>/", TopicDetailView.as_view(), name="topic-detail"),
    path(
        "spaces/<uuid:space_id>/roles/",
        RoleListCreateView.as_view(),
        name="role-list",
    ),
    path("roles/<uuid:role_id>/", RoleDetailView.as_view(), name="role-detail"),
]
