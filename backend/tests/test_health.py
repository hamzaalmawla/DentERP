"""GET /health/ reports the database and Redis."""

from unittest import mock

import pytest
from django.db import OperationalError
from django.test import override_settings

# A port nothing listens on, so the Redis connection is refused at once.
UNREACHABLE_REDIS = "redis://127.0.0.1:1/0"

pytestmark = pytest.mark.django_db


def test_returns_200_when_database_and_redis_are_up(client):
    response = client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {"database": "ok", "redis": "ok"},
    }


def test_returns_503_when_redis_is_down(client):
    with override_settings(REDIS_URL=UNREACHABLE_REDIS):
        response = client.get("/health/")

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "checks": {"database": "ok", "redis": "error"},
    }


def test_returns_503_when_database_is_down(client):
    with mock.patch(
        "config.health.connection.cursor", side_effect=OperationalError("connection refused")
    ):
        response = client.get("/health/")

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "checks": {"database": "error", "redis": "ok"},
    }


def test_returns_503_when_both_are_down(client):
    with (
        override_settings(REDIS_URL=UNREACHABLE_REDIS),
        mock.patch("config.health.connection.cursor", side_effect=OperationalError("down")),
    ):
        response = client.get("/health/")

    assert response.status_code == 503
    assert response.json()["checks"] == {"database": "error", "redis": "error"}


def test_is_never_cached(client):
    response = client.get("/health/")

    assert "no-cache" in response["Cache-Control"]


def test_accepts_only_get(client):
    assert client.post("/health/").status_code == 405
