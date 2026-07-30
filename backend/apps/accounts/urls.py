from django.urls import path

from .views import (
    CsrfView,
    CurrentUserView,
    LoginView,
    LogoutView,
    MyProfileView,
    RegisterView,
    UserDetailView,
    UserSearchView,
)

urlpatterns = [
    path("auth/csrf/", CsrfView.as_view(), name="csrf"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", CurrentUserView.as_view(), name="current-user"),
    path("users/me/", MyProfileView.as_view(), name="my-profile"),
    path("users/", UserSearchView.as_view(), name="user-search"),
    path("users/<uuid:user_id>/", UserDetailView.as_view(), name="user-detail"),
]
