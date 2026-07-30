from django.db import transaction

from .models import Notification


def serialize_notification(notification: Notification) -> dict:
    from .serializers import NotificationSerializer

    notification = Notification.objects.select_related("actor").get(
        pk=notification.pk
    )
    return NotificationSerializer(notification).data


def _schedule_notification_event(notification: Notification):
    notification_id = notification.pk
    recipient_id = str(notification.recipient_id)

    def publish():
        from apps.messaging.realtime import broadcast_user_event

        current = Notification.objects.filter(pk=notification_id).first()
        if current:
            broadcast_user_event(
                recipient_id,
                "notification.created",
                serialize_notification(current),
            )

    transaction.on_commit(publish)


def create_notification(
    *,
    recipient,
    event_type,
    actor=None,
    space=None,
    message=None,
) -> Notification:
    values = {
        "actor": actor,
        "space": space,
    }
    if message is not None:
        notification, created = Notification.objects.get_or_create(
            recipient=recipient,
            event_type=event_type,
            message=message,
            defaults=values,
        )
    else:
        notification = Notification.objects.create(
            recipient=recipient,
            event_type=event_type,
            message=None,
            **values,
        )
        created = True
    if created:
        _schedule_notification_event(notification)
    return notification


def create_message_notifications(message):
    recipients = (
        message.space.memberships.select_related("user")
        .exclude(user_id=message.sender_id)
    )
    for membership in recipients:
        create_notification(
            recipient=membership.user,
            actor=message.sender,
            event_type=Notification.EventType.MESSAGE_CREATED,
            space=message.space,
            message=message,
        )
