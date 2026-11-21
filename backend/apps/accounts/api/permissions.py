"""Role checks for API views (design section 8, layer 1). Every module uses these:

    class ApprovalsView(APIView):
        permission_classes = [IsSupervisor]

    class MediaUploadView(APIView):
        permission_classes = [HasAnyRole(RoleCode.STUDENT, RoleCode.SUPERVISOR)]

The check uses the role the user is acting in now (``X-Active-Role``, or their only role). A
user who holds the role but is acting in another one is refused, so each interface sees only
its own endpoints.
"""

from rest_framework.permissions import BasePermission

from apps.accounts.domain.roles import RoleCode, require_active_role
from apps.core.domain.errors import AccessDeniedError

from .context import request_auth


class _RolePermission(BasePermission):
    allowed_roles: frozenset[str] = frozenset()

    def has_permission(self, request, view) -> bool:
        auth = request_auth(request)
        if auth is None:
            return False  # DRF answers 401 not_authenticated
        if require_active_role(auth.active_role) not in self.allowed_roles:
            raise AccessDeniedError()
        return True


def HasAnyRole(*roles: str) -> type[BasePermission]:
    """A permission class that lets in users acting in any of these roles."""
    unknown = set(roles) - set(RoleCode)
    if not roles or unknown:
        raise ValueError(f"Unknown roles: {sorted(unknown) or 'none given'}")
    name = "HasAnyRole_" + "_".join(sorted(roles))
    return type(name, (_RolePermission,), {"allowed_roles": frozenset(roles)})


IsSuperAdmin = HasAnyRole(RoleCode.SUPER_ADMIN)
IsManagement = HasAnyRole(RoleCode.MANAGEMENT)
IsReception = HasAnyRole(RoleCode.RECEPTION)
IsSupervisor = HasAnyRole(RoleCode.SUPERVISOR)
IsStudent = HasAnyRole(RoleCode.STUDENT)
IsTechnician = HasAnyRole(RoleCode.TECHNICIAN)
