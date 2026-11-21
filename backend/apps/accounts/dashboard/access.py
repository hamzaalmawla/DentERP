"""Who is using the dashboard and in which role (design section 8).

The dashboard keeps Django's session login. Each request reads the user's roles again, so a
role removed or a user deactivated by the administrator takes effect at once. The role the
user acts in is kept in the session: a user with one dashboard role acts in it; a user with
several chooses one (``/dashboard/role/``) and can switch from the account menu.
"""

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied

from apps.accounts import container
from apps.accounts.domain.roles import DASHBOARD_ROLES
from apps.core.application.dtos import Actor

SESSION_ROLE_KEY = "dashboard_active_role"
_CACHE_ATTRIBUTE = "_dashboard_access"


@dataclass(frozen=True, slots=True)
class DashboardAccess:
    user_id: int
    roles: frozenset[str]  # the dashboard roles the user holds
    active_role: str | None
    must_change_password: bool

    @property
    def actor(self) -> Actor:
        if self.active_role is None:
            raise PermissionDenied
        return Actor(user_id=self.user_id, role=self.active_role)


def dashboard_access(request) -> DashboardAccess | None:
    """The logged-in user's dashboard roles and active role; ``None`` when nobody is logged in
    or the user holds no dashboard role."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return None
    cached = getattr(request, _CACHE_ATTRIBUTE, None)
    if cached is not None and cached.user_id == user.pk:
        return cached
    context = container.get_auth_context().execute(user.pk)
    if context is None:
        return None
    roles = context.roles & DASHBOARD_ROLES
    if not roles:
        return None
    chosen = request.session.get(SESSION_ROLE_KEY)
    if chosen in roles:
        active = chosen
    elif len(roles) == 1:
        active = next(iter(roles))
    else:
        active = None
    access = DashboardAccess(
        user_id=user.pk,
        roles=roles,
        active_role=active,
        must_change_password=context.must_change_password,
    )
    setattr(request, _CACHE_ATTRIBUTE, access)
    return access


def choose_role(request, role: str) -> None:
    """Act in ``role`` from now on. The user must hold it as a dashboard role."""
    access = dashboard_access(request)
    if access is None or role not in access.roles:
        raise PermissionDenied
    request.session[SESSION_ROLE_KEY] = role
    if hasattr(request, _CACHE_ATTRIBUTE):
        delattr(request, _CACHE_ATTRIBUTE)


def dashboard_actor(request) -> Actor:
    """The ``Actor`` that dashboard screens pass to services."""
    access = dashboard_access(request)
    if access is None:
        raise PermissionDenied
    return access.actor
