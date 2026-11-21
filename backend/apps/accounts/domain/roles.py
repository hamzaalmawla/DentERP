"""The six roles of the system (design section 8) and how a request picks one of them."""

from collections.abc import Iterable
from enum import StrEnum

from .errors import ActiveRoleRequiredError, RoleNotHeldError


class RoleCode(StrEnum):
    """Role codes. The ``Role`` table holds one row per code (loaded by a data migration)."""

    SUPER_ADMIN = "super_admin"
    MANAGEMENT = "management"
    RECEPTION = "reception"
    SUPERVISOR = "supervisor"
    STUDENT = "student"
    TECHNICIAN = "technician"


ALL_ROLES: frozenset[str] = frozenset(RoleCode)


def resolve_active_role(held: Iterable[str], requested: str | None) -> str | None:
    """The role the user is acting in now (``X-Active-Role``).

    - A requested role must be one the user holds, otherwise ``role_not_held``.
    - With no request, a user with exactly one role acts in it; a user with several roles has
      no active role until they choose one (endpoints that need a role then refuse with
      ``active_role_required``).
    """
    roles = frozenset(held)
    if requested:
        if requested not in roles:
            raise RoleNotHeldError(requested)
        return requested
    if len(roles) == 1:
        return next(iter(roles))
    return None


def require_active_role(active_role: str | None) -> str:
    if active_role is None:
        raise ActiveRoleRequiredError()
    return active_role
