"""Root HTTP routes for the versioned EchoMessenger API."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.common.urls")),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.spaces.urls")),
    path("api/v1/", include("apps.messaging.urls")),
    path("api/v1/", include("apps.notifications.urls")),
]

if settings.DEBUG:
    # Keep attachment storage private even in local development. Only the two
    # intentionally public avatar prefixes are served directly.
    urlpatterns += [
        re_path(
            r"^media/avatars/(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT / "avatars"},
        ),
        re_path(
            r"^media/space-avatars/(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT / "space-avatars"},
        ),
    ]
