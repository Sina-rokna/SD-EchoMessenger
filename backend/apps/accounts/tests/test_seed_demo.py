import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.messaging.models import Message
from apps.spaces.models import ChatSpace, Topic

User = get_user_model()


@pytest.mark.django_db(transaction=True)
def test_seed_demo_is_idempotent(capsys):
    call_command("seed_demo")
    first_counts = (
        User.objects.count(),
        ChatSpace.objects.count(),
        Topic.objects.count(),
        Message.objects.count(),
    )

    call_command("seed_demo")
    second_counts = (
        User.objects.count(),
        ChatSpace.objects.count(),
        Topic.objects.count(),
        Message.objects.count(),
    )

    output = capsys.readouterr().out
    assert first_counts == second_counts == (4, 3, 2, 6)
    assert "DemoPass123!" in output
