"""The current user and IP: request middleware and acting_as."""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, override_settings

from apps.core.infrastructure.request_context import (
    CurrentRequestMiddleware,
    acting_as,
    client_ip,
    current_ip,
    current_user,
    current_user_id,
)

factory = RequestFactory()


def test_nothing_outside_a_request():
    assert current_user_id() is None
    assert current_ip() is None
    assert current_user() is None


def test_middleware_keeps_the_request_only_while_it_runs():
    request = factory.get("/", REMOTE_ADDR="10.0.0.1")
    request.user = AnonymousUser()
    seen = []

    def view(req):
        seen.append(current_ip())
        return "response"

    assert CurrentRequestMiddleware(view)(request) == "response"
    assert seen == ["10.0.0.1"]
    assert current_ip() is None


def test_acting_as_nests_and_restores():
    with acting_as(1):
        with acting_as(None):
            assert current_user_id() is None
        assert current_user_id() == 1
    assert current_user_id() is None


@pytest.mark.django_db
def test_current_user_from_acting_as(user):
    with acting_as(user.pk):
        assert current_user() == user


class TestClientIp:
    def test_remote_addr_without_proxies(self):
        request = factory.get("/", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.2.3.4")

        assert client_ip(request) == "10.0.0.1"  # a spoofed header is ignored

    @override_settings(NUM_PROXIES=1)
    def test_last_forwarded_address_behind_one_proxy(self):
        request = factory.get(
            "/", REMOTE_ADDR="172.18.0.2", HTTP_X_FORWARDED_FOR="6.6.6.6, 203.0.113.9"
        )

        assert client_ip(request) == "203.0.113.9"

    @override_settings(NUM_PROXIES=1)
    def test_falls_back_to_remote_addr(self):
        assert client_ip(factory.get("/", REMOTE_ADDR="10.0.0.1")) == "10.0.0.1"
