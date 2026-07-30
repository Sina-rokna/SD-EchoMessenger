from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db.models import Q
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    LoginSerializer,
    ProfileUpdateSerializer,
    RegistrationSerializer,
    UserPrivateSerializer,
    UserPublicSerializer,
    UserSearchSerializer,
    find_login_user,
)

User = get_user_model()


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    def get(self, request):
        return Response({"csrf_token": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class RegisterView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()
    throttle_scope = "register"

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user)
        return Response(
            UserPrivateSerializer(user, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        candidate = find_login_user(serializer.validated_data["email"])
        user = None
        if candidate:
            user = authenticate(
                request,
                username=candidate.username,
                password=serializer.validated_data["password"],
            )
        if user is None:
            return Response(
                {"detail": "Invalid email or password."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        login(request, user)
        return Response(
            UserPrivateSerializer(user, context={"request": request}).data
        )


class LogoutView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return Response(
            UserPrivateSerializer(
                request.user,
                context={"request": request},
            ).data
        )


class MyProfileView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserPrivateSerializer(user, context={"request": request}).data
        )


class UserDetailView(generics.RetrieveAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserPublicSerializer
    queryset = User.objects.filter(is_active=True)
    lookup_url_kwarg = "user_id"


class UserSearchView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserSearchSerializer

    def get_queryset(self):
        term = self.request.query_params.get("search", "").strip()
        if not term:
            return User.objects.none()
        return (
            User.objects.filter(
                Q(username__icontains=term) | Q(email__icontains=term),
                is_active=True,
            )
            .exclude(pk=self.request.user.pk)
            .order_by("username")[:20]
        )
