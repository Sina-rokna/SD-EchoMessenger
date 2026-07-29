import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


def csrf_client():
    client = APIClient(enforce_csrf_checks=True)
    response = client.get("/api/v1/auth/csrf/")
    assert response.status_code == 200
    client.credentials(HTTP_X_CSRFTOKEN=response.data["csrf_token"])
    return client


@pytest.mark.django_db
def test_registration_requires_csrf_and_hashes_password():
    payload = {
        "username": "alice",
        "email": "Alice@Example.com",
        "password": "SafePassword!123",
    }
    untrusted = APIClient(enforce_csrf_checks=True)
    assert untrusted.post("/api/v1/auth/register/", payload).status_code == 403

    client = csrf_client()
    response = client.post("/api/v1/auth/register/", payload)

    assert response.status_code == 201
    user = User.objects.get(username="alice")
    assert user.email == "alice@example.com"
    assert user.check_password(payload["password"])
    assert response.data["id"] == str(user.pk)
    assert response.data["group_invite_policy"] == "EVERYONE"
    assert client.get("/api/v1/auth/me/").status_code == 200


@pytest.mark.django_db
def test_duplicate_email_and_username_are_case_insensitive():
    User.objects.create_user(
        username="Alice",
        email="alice@example.com",
        password="SafePassword!123",
    )
    client = csrf_client()

    duplicate_email = client.post(
        "/api/v1/auth/register/",
        {
            "username": "different",
            "email": "ALICE@example.com",
            "password": "SafePassword!123",
        },
    )
    duplicate_username = client.post(
        "/api/v1/auth/register/",
        {
            "username": "alice",
            "email": "different@example.com",
            "password": "SafePassword!123",
        },
    )

    assert duplicate_email.status_code == 400
    assert "email" in duplicate_email.data
    assert duplicate_username.status_code == 400
    assert "username" in duplicate_username.data


@pytest.mark.django_db
def test_login_requires_csrf_and_uses_email():
    user = User.objects.create_user(
        username="alice",
        email="alice@example.com",
        password="SafePassword!123",
    )
    payload = {"email": "ALICE@example.com", "password": "SafePassword!123"}
    untrusted = APIClient(enforce_csrf_checks=True)
    assert untrusted.post("/api/v1/auth/login/", payload).status_code == 403

    client = csrf_client()
    response = client.post("/api/v1/auth/login/", payload)

    assert response.status_code == 200
    assert response.data["id"] == str(user.pk)
    assert client.get("/api/v1/auth/me/").status_code == 200


@pytest.mark.django_db
def test_bad_login_does_not_reveal_whether_email_exists():
    User.objects.create_user(
        username="alice",
        email="alice@example.com",
        password="SafePassword!123",
    )
    client = csrf_client()

    wrong_password = client.post(
        "/api/v1/auth/login/",
        {"email": "alice@example.com", "password": "wrong"},
    )
    missing_user = client.post(
        "/api/v1/auth/login/",
        {"email": "missing@example.com", "password": "wrong"},
    )

    assert wrong_password.status_code == missing_user.status_code == 400
    assert wrong_password.data == missing_user.data


@pytest.mark.django_db
def test_profile_update_and_public_profile_do_not_leak_email():
    alice = User.objects.create_user(
        username="alice",
        email="alice@example.com",
        password="SafePassword!123",
    )
    bob = User.objects.create_user(
        username="bob",
        email="bob@example.com",
        password="SafePassword!123",
    )
    client = APIClient()
    client.force_authenticate(alice)

    updated = client.patch(
        "/api/v1/users/me/",
        {
            "bio": "Building EchoMessenger.",
            "group_invite_policy": "NOBODY",
        },
        format="json",
    )
    public = client.get(f"/api/v1/users/{bob.pk}/")

    assert updated.status_code == 200
    assert updated.data["group_invite_policy"] == "NOBODY"
    assert public.status_code == 200
    assert "email" not in public.data


@pytest.mark.django_db
def test_user_search_is_authenticated_and_excludes_requester():
    alice = User.objects.create_user(
        username="alice",
        email="alice@example.com",
        password="SafePassword!123",
    )
    bob = User.objects.create_user(
        username="bobby",
        email="bob@example.com",
        password="SafePassword!123",
    )
    client = APIClient()
    assert client.get("/api/v1/users/?search=bob").status_code == 403

    client.force_authenticate(alice)
    response = client.get("/api/v1/users/?search=bob")

    assert response.status_code == 200
    assert [item["id"] for item in response.data["results"]] == [str(bob.pk)]
