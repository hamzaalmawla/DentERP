"""The web dashboard shell (design sections 8 and 11): a driving adapter, like ``api/``.

What other modules use from here, in their ``admin.py``:

    from apps.accounts.dashboard import (
        Group, ReadOnlyForManagement, dashboard_actor, register_screen,
    )
    from apps.core.dashboard import DashboardModelAdmin

    @admin.register(Clinic)
    class ClinicAdmin(ReadOnlyForManagement, DashboardModelAdmin):
        def save_model(self, request, obj, form, change):
            container.save_clinic().execute(dashboard_actor(request), ...)

    register_screen(Group.FACILITIES, model=Clinic, title=_("Clinics"), icon="apartment")

The site itself is ``site.DashboardSite``; ``config.apps.DashboardAdminConfig`` makes it the
default admin site.
"""

from .access import DashboardAccess, dashboard_access, dashboard_actor
from .navigation import GROUP_TITLES, ROLE_GROUPS, Group, register_screen
from .permissions import ReadOnlyForManagement

__all__ = [
    "GROUP_TITLES",
    "ROLE_GROUPS",
    "DashboardAccess",
    "Group",
    "ReadOnlyForManagement",
    "dashboard_access",
    "dashboard_actor",
    "register_screen",
]
