"""Small unauthenticated probes for container orchestration."""

import asyncio

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import connections
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny


@never_cache
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def live(request):
    """Report that the Django process can serve requests."""

    return JsonResponse({"status": "ok"})


def _database_is_ready() -> None:
    with connections["default"].cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()


def _channel_layer_is_ready() -> None:
    channel_layer = get_channel_layer()
    if channel_layer is None:
        raise RuntimeError("No channel layer is configured.")

    async def round_trip() -> None:
        channel_name = await channel_layer.new_channel("health.")
        marker = {"type": "health.check", "value": "ok"}
        await channel_layer.send(channel_name, marker)
        received = await asyncio.wait_for(
            channel_layer.receive(channel_name),
            timeout=2,
        )
        if received != marker:
            raise RuntimeError("Channel layer readiness round trip failed.")

    async_to_sync(round_trip)()


@never_cache
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def ready(request):
    """Check dependencies required by HTTP and WebSocket request handling."""

    checks: dict[str, str] = {}
    status_code = 200

    for name, check in (
        ("database", _database_is_ready),
        ("channel_layer", _channel_layer_is_ready),
    ):
        try:
            check()
            checks[name] = "ok"
        except Exception:
            # Avoid exposing connection strings or infrastructure details.
            checks[name] = "unavailable"
            status_code = 503

    overall = "ok" if status_code == 200 else "unavailable"
    return JsonResponse(
        {"status": overall, "checks": checks},
        status=status_code,
    )
