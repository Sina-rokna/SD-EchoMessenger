"""Combined WebSocket URL patterns."""

from apps.messaging.routing import websocket_urlpatterns as messaging_patterns
from apps.notifications.routing import websocket_urlpatterns as notification_patterns

websocket_urlpatterns = [*messaging_patterns, *notification_patterns]
