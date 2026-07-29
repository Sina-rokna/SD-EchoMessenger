"""Celery entry points for restart-safe scheduled-message delivery."""

from __future__ import annotations

import logging

from celery import shared_task
from django.db import InterfaceError, OperationalError, transaction
from django.utils import timezone

from .models import Message
from .services import dispatch_scheduled_message

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(OperationalError, InterfaceError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
    name="apps.messaging.tasks.dispatch_due_messages",
)
def dispatch_due_messages(self, batch_size: int = 100) -> dict[str, int]:
    """Dispatch a bounded batch of due messages.

    Beat runs this scanner every five seconds. The database is authoritative:
    a worker claims candidates with ``select_for_update(skip_locked=True)``,
    then ``dispatch_scheduled_message`` status-checks each row again.
    Overlapping workers and retries therefore cannot send the same message
    twice.
    """

    batch_size = max(1, min(int(batch_size), 1_000))
    with transaction.atomic():
        due_ids = list(
            Message.objects.select_for_update(skip_locked=True)
            .filter(
                status=Message.Status.PENDING,
                scheduled_for__lte=timezone.now(),
            )
            .order_by("scheduled_for", "created_at")
            .values_list("pk", flat=True)[:batch_size]
        )

        sent = 0
        skipped = 0
        for message_id in due_ids:
            if dispatch_scheduled_message(message_id):
                sent += 1
            else:
                # Includes cancellation and a permission/topic failure
                # recorded by the domain service.
                skipped += 1

    if due_ids:
        logger.info(
            "Scheduled-message scan completed: candidates=%d sent=%d skipped=%d",
            len(due_ids),
            sent,
            skipped,
        )
    return {
        "candidates": len(due_ids),
        "sent": sent,
        "skipped": skipped,
    }
