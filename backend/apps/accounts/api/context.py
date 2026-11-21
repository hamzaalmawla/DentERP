"""Who is calling and in which role (design section 8, layer 1).

``request_auth(request)`` reads the user's roles and password gate once per request and keeps
the result on the request. ``request_actor(request)`` gives the ``Actor`` (user and active
role) that views pass to services and query services:

    def get(self, request):
        actor = request_actor(request)  # 403 active_role_required if no role is chosen
        return Response(...(container.patient_queries().list(actor)))
"""

from dataclasses import dataclass

from django.http import HttpRequest
from rest_framework.exceptions import NotAuthenticated

from apps.accounts import container
from apps.accounts.domain.roles import require_active_role, resolve_active_role
from apps.core.application.dtos import Actor

ACTIVE_ROLE_HEADER = "X-Active-Role"

_CACHE_ATTRIBUTE = "_accounts_request_auth"


@dataclass(frozen=True, slots=True)
class RequestAuth:
    user_id: int
    roles: frozenset[str]
    active_role: str | None
    must_change_password: bool

    @property
    def actor(self) -> Actor:
        return Actor(user_id=self.user_id, role=require_active_role(self.active_role))


def _django_request(request) -> HttpRequest:
    return getattr(request, "_request", request)  # a DRF Request wraps the HttpRequest


def request_auth(request, user=None) -> RequestAuth | None:
    """The caller's roles and active role, or ``None`` when nobody is logged in.

    Raises ``role_not_held`` when ``X-Active-Role`` names a role the user does not hold.
    """
    django_request = _django_request(request)
    cached = getattr(django_request, _CACHE_ATTRIBUTE, None)
    user = user if user is not None else getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return None
    if cached is not None and cached.user_id == user.pk:
        return cached
    context = container.get_auth_context().execute(user.pk)
    if context is None:
        return None
    requested = django_request.headers.get(ACTIVE_ROLE_HEADER, "").strip() or None
    auth = RequestAuth(
        user_id=context.user_id,
        roles=context.roles,
        active_role=resolve_active_role(context.roles, requested),
        must_change_password=context.must_change_password,
    )
    setattr(django_request, _CACHE_ATTRIBUTE, auth)
    return auth


def request_actor(request) -> Actor:
    """The ``Actor`` for services. 401 when not logged in, 403 ``active_role_required`` when a
    user with several roles has not chosen one."""
    auth = request_auth(request)
    if auth is None:
        raise NotAuthenticated()
    return auth.actor
