from django.apps import AppConfig


class MessagingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.messaging"
    verbose_name = "Messaging"

    def ready(self):
        # Register storage cleanup for explicit and cascading database deletes.
        from . import signals  # noqa: F401
