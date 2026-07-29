"""Authenticated personal notification WebSocket stream."""

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.messaging.realtime import notification_group_name


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self) -> None:
        user = self.scope.get("user")
        if user is None or not user.is_authenticated or not user.is_active:
            await self.close(code=4401)
            return

        self.group_name = notification_group_name(user.pk)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        group_name = getattr(self, "group_name", None)
        if group_name:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def receive_json(self, content, **kwargs) -> None:
        if not await self._is_active_user():
            await self.close(code=4401)
            return

        if content.get("type") == "ping":
            await self.send_json({"type": "pong"})
            return

        await self.send_json(
            {
                "type": "error",
                "code": "unsupported_action",
                "detail": "Notification sockets are read-only.",
            }
        )

    async def realtime_event(self, event) -> None:
        if not await self._is_active_user():
            await self.close(code=4401)
            return
        await self.send_json(event["envelope"])

    @database_sync_to_async
    def _is_active_user(self) -> bool:
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            return False
        return user.__class__.objects.filter(pk=user.pk, is_active=True).exists()
