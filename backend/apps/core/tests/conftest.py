import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.fixture
def make_user(db):
    def make(username: str = "user"):
        return get_user_model().objects.create_user(username=username, password="x-Pass-2026")

    return make


@pytest.fixture
def user(make_user):
    return make_user("alice")


@pytest.fixture
def api(user):
    client = APIClient()
    client.force_authenticate(user)
    return client
