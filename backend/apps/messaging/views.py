from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import parsers, permissions, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.spaces.models import ChatSpace
from apps.spaces.services import is_member, require_member

from .models import Attachment, Message
from .pagination import MessagePagination
from .serializers import (
    MessageCreateSerializer,
    MessageEditSerializer,
    MessageSerializer,
    ScheduledMessageUpdateSerializer,
)
from .services import (
    cancel_scheduled_message,
    create_message,
    delete_sent_message,
    edit_sent_message,
    update_scheduled_message,
)


def message_queryset():
    return Message.objects.select_related(
        "space",
        "topic",
        "sender",
    ).prefetch_related("attachments")


def visible_space(request, space_id):
    space = get_object_or_404(ChatSpace, pk=space_id)
    require_member(request.user, space)
    return space


class SpaceMessageListCreateView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (
        parsers.JSONParser,
        parsers.MultiPartParser,
        parsers.FormParser,
    )
    throttle_scope = "messages"

    def get(self, request, space_id):
        space = visible_space(request, space_id)
        messages = message_queryset().filter(
            space=space,
            status=Message.Status.SENT,
        ).order_by("-sent_at", "-created_at", "-id")
        topic_id = request.query_params.get("topic")
        if topic_id:
            messages = messages.filter(topic_id=topic_id)
        paginator = MessagePagination()
        page = paginator.paginate_queryset(messages, request, view=self)
        serializer = MessageSerializer(
            page,
            many=True,
            context={"request": request},
        )
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, space_id):
        space = visible_space(request, space_id)
        data = request.data.copy()
        if hasattr(data, "pop"):
            data.pop("attachments", None)
        serializer = MessageCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        files = request.FILES.getlist("attachments")
        values = serializer.validated_data
        message, created = create_message(
            actor=request.user,
            space=space,
            text=values.get("text", ""),
            topic=values.get("topic"),
            files=files,
            scheduled_for=values.get("scheduled_for"),
            client_nonce=values.get("client_nonce"),
        )
        message = message_queryset().get(pk=message.pk)
        return Response(
            MessageSerializer(
                message,
                context={"request": request},
            ).data,
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )


class MessageSearchView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, space_id):
        space = visible_space(request, space_id)
        query = request.query_params.get("q", "").strip()
        if not query:
            raise ValidationError({"q": "Enter a search term."})
        messages = message_queryset().filter(
            space=space,
            status=Message.Status.SENT,
            text__icontains=query,
        ).order_by("-sent_at", "-created_at", "-id")
        topic_id = request.query_params.get("topic")
        if topic_id:
            messages = messages.filter(topic_id=topic_id)
        paginator = MessagePagination()
        page = paginator.paginate_queryset(messages, request, view=self)
        serializer = MessageSerializer(
            page,
            many=True,
            context={"request": request},
        )
        return paginator.get_paginated_response(serializer.data)


class MessageDetailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def _message(self, request, message_id):
        message = get_object_or_404(message_queryset(), pk=message_id)
        if not is_member(request.user, message.space):
            raise NotFound("Message not found.")
        return message

    def patch(self, request, message_id):
        message = self._message(request, message_id)
        serializer = MessageEditSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = edit_sent_message(
            actor=request.user,
            message=message,
            text=serializer.validated_data["text"],
        )
        return Response(
            MessageSerializer(
                message_queryset().get(pk=message.pk),
                context={"request": request},
            ).data
        )

    def delete(self, request, message_id):
        message = self._message(request, message_id)
        delete_sent_message(actor=request.user, message=message)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ScheduledMessageListView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        messages = message_queryset().filter(
            sender=request.user,
            status=Message.Status.PENDING,
        ).order_by("scheduled_for", "id")
        paginator = MessagePagination()
        page = paginator.paginate_queryset(messages, request, view=self)
        serializer = MessageSerializer(
            page,
            many=True,
            context={"request": request},
        )
        return paginator.get_paginated_response(serializer.data)


class ScheduledMessageDetailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def _message(self, request, message_id):
        message = get_object_or_404(
            message_queryset(),
            pk=message_id,
            sender=request.user,
        )
        if message.status != Message.Status.PENDING:
            raise NotFound("Pending message not found.")
        return message

    def patch(self, request, message_id):
        message = self._message(request, message_id)
        serializer = ScheduledMessageUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        message = update_scheduled_message(
            actor=request.user,
            message=message,
            text=values.get("text") if "text" in values else None,
            topic=values.get("topic") if "topic" in values else None,
            scheduled_for=(
                values.get("scheduled_for")
                if "scheduled_for" in values
                else None
            ),
        )
        return Response(
            MessageSerializer(
                message_queryset().get(pk=message.pk),
                context={"request": request},
            ).data
        )

    def delete(self, request, message_id):
        message = self._message(request, message_id)
        cancel_scheduled_message(actor=request.user, message=message)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AttachmentDownloadView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, attachment_id):
        attachment = get_object_or_404(
            Attachment.objects.select_related("message__space"),
            pk=attachment_id,
        )
        if not is_member(request.user, attachment.message.space):
            raise NotFound("Attachment not found.")
        try:
            file_handle = attachment.file.open("rb")
        except FileNotFoundError as exc:
            raise NotFound("Attachment file not found.") from exc
        response = FileResponse(
            file_handle,
            as_attachment=False,
            filename=attachment.original_name,
            content_type=attachment.content_type,
        )
        response["Content-Length"] = attachment.size
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        return response
