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
"""

from unfold.admin import ModelAdmin


class DashboardModelAdmin(ModelAdmin):
    def _site_allows(self, request, action: str) -> bool:
        allows = getattr(self.admin_site, "allows", None)
        return bool(allows is not None and allows(request, self.model, action))

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
