"""Read-only WebSocket stream for one chat space."""

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.spaces.models import SpaceMembership

from .realtime import space_group_name


class SpaceConsumer(AsyncJsonWebsocketConsumer):
    """Deliver committed chat events to authenticated space members."""

    async def connect(self) -> None:
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.space_id = str(self.scope["url_route"]["kwargs"]["space_id"])
        if not await self._is_member():
            await self.close(code=4403)
            return

        self.group_name = space_group_name(self.space_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        group_name = getattr(self, "group_name", None)
        if group_name:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def receive_json(self, content, **kwargs) -> None:
        # REST owns all mutations. A tiny ping action lets clients verify that
        # a reconnected socket is still authorized.
        if not await self._is_member():
            await self.close(code=4403)
            return

        if content.get("type") == "ping":
            await self.send_json({"type": "pong"})
            return

        await self.send_json(
            {
                "type": "error",
                "code": "unsupported_action",
                "detail": "WebSockets deliver events; use the REST API for writes.",
            }
        )

    async def realtime_event(self, event) -> None:
        # Membership can be revoked while a socket is open. Recheck before
        # disclosing each new event.
        if not await self._is_member():
            await self.close(code=4403)
            return
        await self.send_json(event["envelope"])

    @database_sync_to_async
    def _is_member(self) -> bool:
        user = self.scope.get("user")
        if user is None or not user.is_authenticated or not user.is_active:
            return False
        return SpaceMembership.objects.filter(
            space_id=self.space_id,
            user_id=user.pk,
        ).exists()
