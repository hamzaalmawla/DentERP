"""The base of every dashboard screen (design section 11).

Every ``ModelAdmin`` of the system inherits ``DashboardModelAdmin``; the dashboard site refuses
any other class. Who may open a screen is not decided here: core does not know the roles
(accounts owns them), so each permission check asks the site (``admin_site.allows``), which
reads the user's active role and the role → groups map. A site without that check (Django's
plain ``AdminSite``) opens nothing.

The rules that hold for every screen are kept here:

- Records are never deleted (SYS-10): there is no delete permission and no delete action.
  Screens that end a record call a service that deactivates it.
- What changed is written to ``AuditLog`` by the services, so Django's own admin log
  (``LogEntry``) is not written.

A screen narrows these further by overriding a permission method and calling ``super()``,
for example a read-only screen returns ``False`` from ``has_add_permission``.

A screen passes the user to services as ``self.actor(request)``: the site knows the user's
active role, core does not.

Inlines inherit ``DashboardTabularInline``: an inline is part of its screen, so it opens for
the roles that may open the screen (``parent_model``), and its rows are never deleted.
"""

from django.core.exceptions import PermissionDenied
from unfold.admin import ModelAdmin, TabularInline

from apps.core.application.dtos import Actor


def _site_allows(admin_site, request, model, action: str) -> bool:
    allows = getattr(admin_site, "allows", None)
    return bool(allows is not None and allows(request, model, action))


class DashboardModelAdmin(ModelAdmin):
    def _site_allows(self, request, action: str) -> bool:
        return _site_allows(self.admin_site, request, self.model, action)

    def actor(self, request) -> Actor:
        """The user and the role they act in, for services. 403 when the site cannot tell."""
        actor = getattr(self.admin_site, "actor", None)
        if actor is None:
            raise PermissionDenied
        return actor(request)

    def has_module_permission(self, request) -> bool:
        return self._site_allows(request, "view")

    def has_view_permission(self, request, obj=None) -> bool:
        return self._site_allows(request, "view")

    def has_add_permission(self, request) -> bool:
        return self._site_allows(request, "add")

    def has_change_permission(self, request, obj=None) -> bool:
        return self._site_allows(request, "change")

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    # AuditLog is the one record of what changed (DB-17); the services write it.
    def log_addition(self, request, obj, message):
        return None

    def log_change(self, request, obj, message):
        return None

    def log_deletions(self, request, queryset):
        return None


class DashboardTabularInline(TabularInline):
    """A table of related rows inside a screen. Rows are never deleted (SYS-10)."""

    extra = 0

    def has_view_permission(self, request, obj=None) -> bool:
        return _site_allows(self.admin_site, request, self.parent_model, "view")

    def has_add_permission(self, request, obj=None) -> bool:
        return _site_allows(self.admin_site, request, self.parent_model, "add")

    def has_change_permission(self, request, obj=None) -> bool:
        return _site_allows(self.admin_site, request, self.parent_model, "change")

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
