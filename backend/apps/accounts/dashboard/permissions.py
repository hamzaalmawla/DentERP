"""Permission mixins for dashboard screens (design section 11)."""

from apps.accounts.domain.roles import RoleCode

from .access import dashboard_access


def acting_as_management(request) -> bool:
    access = dashboard_access(request)
    return access is not None and access.active_role == RoleCode.MANAGEMENT


class ReadOnlyForManagement:
    """Management sees its screens but changes nothing: no add, change or delete.

    Put it first in the bases of every admin class and inline:

        class ClinicAdmin(ReadOnlyForManagement, DashboardModelAdmin): ...

    The dashboard site also adds it to any registered admin class that leaves it out, so a
    screen can never forget it.
    """

    def has_add_permission(self, request, *args, **kwargs) -> bool:
        if acting_as_management(request):
            return False
        return super().has_add_permission(request, *args, **kwargs)

    def has_change_permission(self, request, *args, **kwargs) -> bool:
        if acting_as_management(request):
            return False
        return super().has_change_permission(request, *args, **kwargs)

    def has_delete_permission(self, request, *args, **kwargs) -> bool:
        if acting_as_management(request):
            return False
        return super().has_delete_permission(request, *args, **kwargs)
