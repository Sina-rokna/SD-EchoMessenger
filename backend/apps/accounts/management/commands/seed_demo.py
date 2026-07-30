from uuid import NAMESPACE_URL, uuid5

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.messaging.services import create_message
from apps.spaces.models import ChatSpace, Role, SpaceMembership, Topic
from apps.spaces.services import get_or_create_direct_space

User = get_user_model()

DEMO_PASSWORD = "DemoPass123!"
DEMO_USERS = (
    ("alice", "alice@example.test", "Alice owns the demo spaces."),
    ("bob", "bob@example.test", "Bob is a channel moderator."),
    ("carol", "carol@example.test", "Carol is a regular member."),
    ("dave", "dave@example.test", "Dave demonstrates private invitations."),
)


class Command(BaseCommand):
    help = "Create an idempotent EchoMessenger demo workspace."

    @transaction.atomic
    def handle(self, *args, **options):
        users = {
            username: self._user(username, email, bio)
            for username, email, bio in DEMO_USERS
        }
        alice = users["alice"]
        bob = users["bob"]
        carol = users["carol"]
        dave = users["dave"]

        group = self._named_space(
            owner=alice,
            space_type=ChatSpace.Type.GROUP,
            name="Software Design Team",
            members=(alice, bob, carol, dave),
        )
        channel = self._named_space(
            owner=alice,
            space_type=ChatSpace.Type.CHANNEL,
            name="EchoMessenger Community",
            members=(alice, bob, carol),
        )
        default_role, _ = Role.objects.get_or_create(
            space=channel,
            is_default=True,
            defaults={
                "name": "Member",
                "can_send_messages": True,
                "can_send_media": True,
            },
        )
        moderator, _ = Role.objects.update_or_create(
            space=channel,
            name="Moderator",
            defaults={
                "can_send_messages": True,
                "can_send_media": True,
                "can_manage_topics": True,
                "can_manage_members": True,
                "can_delete_messages": True,
                "can_manage_roles": False,
                "can_manage_space": False,
                "is_default": False,
            },
        )
        SpaceMembership.objects.filter(space=channel, user=alice).update(
            role=default_role
        )
        SpaceMembership.objects.filter(space=channel, user=bob).update(
            role=moderator
        )
        SpaceMembership.objects.filter(space=channel, user=carol).update(
            role=default_role
        )
        general, _ = Topic.objects.get_or_create(
            space=channel,
            name="General",
            defaults={"created_by": alice},
        )
        announcements, _ = Topic.objects.get_or_create(
            space=channel,
            name="Announcements",
            defaults={"created_by": alice},
        )
        direct, _ = get_or_create_direct_space(alice, bob)

        self._message(
            sender=alice,
            space=group,
            text="Welcome! This group is where our six-person team coordinates.",
            key="demo-group-welcome",
        )
        self._message(
            sender=carol,
            space=group,
            text="The Phase 2 demo is ready for review.",
            key="demo-group-ready",
        )
        self._message(
            sender=alice,
            space=channel,
            topic=announcements,
            text="EchoMessenger now supports live and scheduled messages.",
            key="demo-channel-announcement",
        )
        self._message(
            sender=bob,
            space=channel,
            topic=general,
            text="Try message search, protected files, and role permissions.",
            key="demo-channel-general",
        )
        self._message(
            sender=alice,
            space=direct,
            text="Hi Bob — this is our canonical direct chat.",
            key="demo-direct-alice",
        )
        self._message(
            sender=bob,
            space=direct,
            text="Received. Opening it again will reuse the same conversation.",
            key="demo-direct-bob",
        )

        self.stdout.write(self.style.SUCCESS("Demo data is ready."))
        self.stdout.write("All demo accounts use this password:")
        self.stdout.write(f"  {DEMO_PASSWORD}")
        for username, email, _ in DEMO_USERS:
            self.stdout.write(f"  {username:<6} {email}")

    def _user(self, username, email, bio):
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={"email": email},
        )
        changed_fields = []
        if user.email != email:
            user.email = email
            changed_fields.append("email")
        if user.bio != bio:
            user.bio = bio
            changed_fields.append("bio")
        if user.group_invite_policy != User.GroupInvitePolicy.EVERYONE:
            user.group_invite_policy = User.GroupInvitePolicy.EVERYONE
            changed_fields.append("group_invite_policy")
        user.set_password(DEMO_PASSWORD)
        changed_fields.append("password")
        user.save(update_fields=changed_fields)
        return user

    def _named_space(self, *, owner, space_type, name, members):
        space, _ = ChatSpace.objects.get_or_create(
            type=space_type,
            name=name,
            created_by=owner,
        )
        for user in members:
            SpaceMembership.objects.get_or_create(space=space, user=user)
        return space

    def _message(self, *, sender, space, text, key, topic=None):
        create_message(
            actor=sender,
            space=space,
            topic=topic,
            text=text,
            client_nonce=uuid5(NAMESPACE_URL, f"echomessenger:{key}"),
        )
