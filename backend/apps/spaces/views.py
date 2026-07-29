from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChatSpace, Role, SpaceMembership, Topic
from .serializers import (
    ChatSpaceSerializer,
    DirectSpaceCreateSerializer,
    MemberAddSerializer,
    MemberRoleUpdateSerializer,
    RoleSerializer,
    SpaceCreateSerializer,
    SpaceMembershipSerializer,
    SpaceUpdateSerializer,
    TopicSerializer,
)
from .services import (
    _schedule_space_event,
    _schedule_user_event,
    add_member,
    assign_role,
    can_manage_roles,
    can_manage_space,
    can_manage_topics,
    create_space,
    get_or_create_direct_space,
    remove_member,
    require_member,
    validate_role_permissions,
    visible_spaces_for,
)


def space_or_404(space_id):
    return get_object_or_404(
        ChatSpace.objects.select_related("created_by").prefetch_related(
            "memberships__user",
            "memberships__role",
        ),
        pk=space_id,
    )


class SpaceListCreateView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        spaces = visible_spaces_for(request.user)
        return Response(
            ChatSpaceSerializer(
                spaces,
                many=True,
                context={"request": request},
            ).data
        )

    def post(self, request):
        serializer = SpaceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        space = create_space(
            actor=request.user,
            space_type=data["type"],
            name=data["name"],
            avatar=data.get("avatar"),
            member_ids=data.get("member_ids", ()),
        )
        _schedule_space_event(
            space,
            "space.updated",
            {"space_id": str(space.pk), "action": "created"},
        )
        space = space_or_404(space.pk)
        return Response(
            ChatSpaceSerializer(
                space,
                context={"request": request},
            ).data,
            status=status.HTTP_201_CREATED,
        )


class DirectSpaceCreateView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = DirectSpaceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        other_user = serializer.validated_data["user"]
        space, created = get_or_create_direct_space(request.user, other_user)
        space = space_or_404(space.pk)
        return Response(
            ChatSpaceSerializer(
                space,
                context={"request": request},
            ).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class SpaceDetailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, space_id):
        space = space_or_404(space_id)
        require_member(request.user, space)
        return Response(
            ChatSpaceSerializer(space, context={"request": request}).data
        )

    @transaction.atomic
    def patch(self, request, space_id):
        space = space_or_404(space_id)
        require_member(request.user, space)
        if not can_manage_space(request.user, space):
            raise PermissionDenied("You cannot edit this space.")
        serializer = SpaceUpdateSerializer(
            space,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        space = serializer.save()
        _schedule_space_event(
            space,
            "space.updated",
            {"space_id": str(space.pk), "action": "updated"},
        )
        return Response(
            ChatSpaceSerializer(space, context={"request": request}).data
        )

    @transaction.atomic
    def delete(self, request, space_id):
        space = space_or_404(space_id)
        require_member(request.user, space)
        if not can_manage_space(request.user, space):
            raise PermissionDenied("You cannot delete this space.")
        payload = {"space_id": str(space.pk), "action": "deleted"}
        peer_ids = list(
            space.memberships.exclude(user=request.user).values_list(
                "user_id",
                flat=True,
            )
        )
        _schedule_space_event(space, "space.updated", payload)
        for peer_id in peer_ids:
            _schedule_user_event(
                peer_id,
                "member.updated",
                {
                    "space_id": str(space.pk),
                    "user_id": str(peer_id),
                    "action": "space_deleted",
                    "role_id": None,
                },
            )
        space.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MemberListCreateView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, space_id):
        space = space_or_404(space_id)
        require_member(request.user, space)
        memberships = space.memberships.select_related("user", "role")
        return Response(SpaceMembershipSerializer(memberships, many=True).data)

    def post(self, request, space_id):
        space = space_or_404(space_id)
        require_member(request.user, space)
        serializer = MemberAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = add_member(
            actor=request.user,
            space=space,
            user=serializer.validated_data["user"],
            role=serializer.validated_data.get("role"),
        )
        membership = SpaceMembership.objects.select_related(
            "user",
            "role",
        ).get(pk=membership.pk)
        return Response(
            SpaceMembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )


class LeaveSpaceView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def delete(self, request, space_id):
        space = space_or_404(space_id)
        membership = require_member(request.user, space)
        remove_member(
            actor=request.user,
            membership=membership,
            self_leave=True,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MemberDetailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def _membership(self, request, space_id, user_id):
        space = space_or_404(space_id)
        require_member(request.user, space)
        return get_object_or_404(
            SpaceMembership.objects.select_related("space", "user", "role"),
            space=space,
            user_id=user_id,
        )

    def patch(self, request, space_id, user_id):
        membership = self._membership(request, space_id, user_id)
        if membership.space.type != ChatSpace.Type.CHANNEL:
            raise ValidationError("Only channel members have roles.")
        serializer = MemberRoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = assign_role(
            actor=request.user,
            membership=membership,
            role=serializer.validated_data["role"],
        )
        return Response(SpaceMembershipSerializer(membership).data)

    def delete(self, request, space_id, user_id):
        membership = self._membership(request, space_id, user_id)
        remove_member(
            actor=request.user,
            membership=membership,
            self_leave=membership.user_id == request.user.pk,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class TopicListCreateView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def _channel(self, request, space_id):
        space = space_or_404(space_id)
        require_member(request.user, space)
        if space.type != ChatSpace.Type.CHANNEL:
            raise ValidationError("Only channels contain topics.")
        return space

    def get(self, request, space_id):
        space = self._channel(request, space_id)
        return Response(TopicSerializer(space.topics.all(), many=True).data)

    @transaction.atomic
    def post(self, request, space_id):
        space = self._channel(request, space_id)
        if not can_manage_topics(request.user, space):
            raise PermissionDenied("You cannot create topics in this channel.")
        serializer = TopicSerializer(
            data=request.data,
            context={"space": space},
        )
        serializer.is_valid(raise_exception=True)
        topic = serializer.save(space=space, created_by=request.user)
        _schedule_space_event(
            space,
            "space.updated",
            {
                "space_id": str(space.pk),
                "action": "topic_created",
                "topic_id": str(topic.pk),
            },
        )
        return Response(
            TopicSerializer(topic).data,
            status=status.HTTP_201_CREATED,
        )


class TopicDetailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def _topic(self, request, topic_id):
        topic = get_object_or_404(
            Topic.objects.select_related("space", "created_by"),
            pk=topic_id,
        )
        require_member(request.user, topic.space)
        if not can_manage_topics(request.user, topic.space):
            raise PermissionDenied("You cannot manage topics in this channel.")
        return topic

    @transaction.atomic
    def patch(self, request, topic_id):
        topic = self._topic(request, topic_id)
        serializer = TopicSerializer(
            topic,
            data=request.data,
            partial=True,
            context={"space": topic.space},
        )
        serializer.is_valid(raise_exception=True)
        topic = serializer.save()
        _schedule_space_event(
            topic.space,
            "space.updated",
            {
                "space_id": str(topic.space_id),
                "action": "topic_updated",
                "topic_id": str(topic.pk),
            },
        )
        return Response(TopicSerializer(topic).data)

    @transaction.atomic
    def delete(self, request, topic_id):
        topic = self._topic(request, topic_id)
        if topic.messages.exists():
            raise ValidationError(
                "A topic with message history cannot be deleted."
            )
        payload = {
            "space_id": str(topic.space_id),
            "action": "topic_deleted",
            "topic_id": str(topic.pk),
        }
        _schedule_space_event(topic.space, "space.updated", payload)
        topic.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoleListCreateView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def _channel(self, request, space_id):
        space = space_or_404(space_id)
        require_member(request.user, space)
        if space.type != ChatSpace.Type.CHANNEL:
            raise ValidationError("Only channels contain roles.")
        return space

    def get(self, request, space_id):
        space = self._channel(request, space_id)
        return Response(RoleSerializer(space.roles.all(), many=True).data)

    @transaction.atomic
    def post(self, request, space_id):
        space = self._channel(request, space_id)
        if not can_manage_roles(request.user, space):
            raise PermissionDenied("You cannot create roles in this channel.")
        serializer = RoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validate_role_permissions(
            request.user,
            space,
            serializer.validated_data,
        )
        role = serializer.save(space=space)
        _schedule_space_event(
            space,
            "space.updated",
            {
                "space_id": str(space.pk),
                "action": "role_created",
                "role_id": str(role.pk),
            },
        )
        return Response(
            RoleSerializer(role).data,
            status=status.HTTP_201_CREATED,
        )


class RoleDetailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def _role(self, request, role_id):
        role = get_object_or_404(
            Role.objects.select_related("space"),
            pk=role_id,
        )
        require_member(request.user, role.space)
        if not can_manage_roles(request.user, role.space):
            raise PermissionDenied("You cannot manage roles in this channel.")
        return role

    @transaction.atomic
    def patch(self, request, role_id):
        role = self._role(request, role_id)
        serializer = RoleSerializer(
            role,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        validate_role_permissions(
            request.user,
            role.space,
            serializer.validated_data,
        )
        role = serializer.save()
        _schedule_space_event(
            role.space,
            "space.updated",
            {
                "space_id": str(role.space_id),
                "action": "role_updated",
                "role_id": str(role.pk),
            },
        )
        return Response(RoleSerializer(role).data)

    @transaction.atomic
    def delete(self, request, role_id):
        role = self._role(request, role_id)
        if role.is_default:
            raise ValidationError("The default channel role cannot be deleted.")
        payload = {
            "space_id": str(role.space_id),
            "action": "role_deleted",
            "role_id": str(role.pk),
        }
        _schedule_space_event(role.space, "space.updated", payload)
        role.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
