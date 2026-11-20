"""Who is acting now, so ``BaseModel`` can fill ``created_by`` / ``updated_by`` and the audit
log can record the user and IP without every call passing them.

Two sources, the first one set wins:

1. ``acting_as(user_id)`` — a service context for work outside a request: Celery tasks,
   management commands, data imports. ``acting_as(None)`` marks work as done by the system.
2. The current request — ``CurrentRequestMiddleware`` keeps it for the length of the request.
   The user is read when it is needed, so token (JWT) logins that DRF authenticates inside the
   view are seen too.

Both use ``contextvars``, so concurrent requests and threads never see each other's user.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponse

_UNSET: Any = object()

_request: ContextVar[HttpRequest | None] = ContextVar("core_current_request", default=None)
_actor_id: ContextVar[int | None] = ContextVar("core_actor_id", default=_UNSET)


@contextmanager
def acting_as(user_id: int | None) -> Iterator[None]:
    """Attribute every save and audit row inside the block to ``user_id`` (``None``: the system)."""
    token = _actor_id.set(user_id)
    try:
        yield
    finally:
        _actor_id.reset(token)


@contextmanager
def bound_request(request: HttpRequest) -> Iterator[None]:
    token = _request.set(request)
    try:
        yield
    finally:
        _request.reset(token)


def _request_user(request: HttpRequest | None) -> Any:
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return user
    return None


def current_user_id() -> int | None:
    actor_id = _actor_id.get()
    if actor_id is not _UNSET:
        return actor_id
    user = _request_user(_request.get())
    return user.pk if user is not None else None


def current_user() -> Any:
    """The acting user as a model instance, or ``None`` (used by django-simple-history)."""
    actor_id = _actor_id.get()
    if actor_id is not _UNSET:
        if actor_id is None:
            return None
        return get_user_model()._base_manager.filter(pk=actor_id).first()
    return _request_user(_request.get())


def client_ip(request: HttpRequest) -> str | None:
    """The client's address. Behind ``NUM_PROXIES`` reverse proxies (nginx in staging and
    production) it is read from ``X-Forwarded-For`` the same way DRF's throttles read it."""
    num_proxies = settings.NUM_PROXIES
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if num_proxies > 0 and forwarded:
        addresses = [address.strip() for address in forwarded.split(",") if address.strip()]
        if addresses:
            return addresses[-min(num_proxies, len(addresses))]
    return request.META.get("REMOTE_ADDR") or None


def current_ip() -> str | None:
    request = _request.get()
    return client_ip(request) if request is not None else None


class CurrentRequestMiddleware:
    """Keeps the request for ``current_user_id`` and ``current_ip``. Goes after
    ``AuthenticationMiddleware`` in ``MIDDLEWARE``."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        with bound_request(request):
            return self.get_response(request)
