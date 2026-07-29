import pytest


@pytest.mark.django_db
def test_liveness_does_not_require_authentication(client):
    response = client.get("/api/v1/health/live/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "no-cache" in response.headers["Cache-Control"]


@pytest.mark.django_db
def test_readiness_checks_database_and_channel_layer(client):
    response = client.get("/api/v1/health/ready/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {
            "database": "ok",
            "channel_layer": "ok",
        },
    }
