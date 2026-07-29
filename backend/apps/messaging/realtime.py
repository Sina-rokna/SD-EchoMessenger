"""Committed WebSocket event helpers.

Domain services call the ``publish_*_on_commit`` functions after a successful
write. Keeping publication behind ``transaction.on_commit`` prevents clients
from observing rows that later roll back.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any
from uuid import UUID, uuid4

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def _identifier(value: UUID | str) -> str:
    return str(value).replace("-", "")


def space_group_name(space_id: UUID | str) -> str:
    return f"space.{_identifier(space_id)}"


def notification_group_name(user_id: UUID | str) -> str:
    return f"user.{_identifier(user_id)}"


def event_envelope(event_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    occurred_at = timezone.now().isoformat().replace("+00:00", "Z")
    return {
        "type": event_type,
        "event_id": str(uuid4()),
        "occurred_at": occurred_at,
        "payload": dict(payload),
    }


def _broadcast(group_name: str, envelope: Mapping[str, Any]) -> bool:
    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.error("Realtime event dropped: no channel layer is configured.")
        return False

    try:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                # Channels maps this name to ``realtime_event`` on the consumer.
                "type": "realtime.event",
                "envelope": dict(envelope),
            },
        )
    except Exception:
        # The database write is already committed by the time this helper is
        # called. Do not report a false write failure to the API client. The
        # durable REST resource/notification remains available after reconnect.
        logger.exception("Realtime event delivery failed for group %s.", group_name)
        return False
    return True


def broadcast_space_event(
    space_id: UUID | str,
    event_type: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    envelope = event_envelope(event_type, payload)
    _broadcast(space_group_name(space_id), envelope)
    return envelope


def broadcast_notification_event(
    user_id: UUID | str,
    event_type: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    envelope = event_envelope(event_type, payload)
    _broadcast(notification_group_name(user_id), envelope)
    return envelope


def broadcast_user_event(
    user_id: UUID | str,
    event_type: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Broadcast a personal event.

    ``broadcast_user_event`` is the domain-facing name; the notification
    consumer receives every personal event, including membership changes.
    """

    return broadcast_notification_event(user_id, event_type, payload)


def publish_space_event_on_commit(
    space_id: UUID | str,
    event_type: str,
    payload: Mapping[str, Any],
) -> None:
    frozen_payload = dict(payload)
    transaction.on_commit(
        lambda: broadcast_space_event(space_id, event_type, frozen_payload)
    )


def publish_notification_on_commit(
    user_id: UUID | str,
    payload: Mapping[str, Any],
) -> None:
    frozen_payload = dict(payload)
    transaction.on_commit(
        lambda: broadcast_notification_event(
            user_id,
            "notification.created",
            frozen_payload,
        )
    )
