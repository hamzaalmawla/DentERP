"""App configs of the project itself."""

from django.contrib.admin.apps import AdminConfig


class DashboardAdminConfig(AdminConfig):
    """``django.contrib.admin`` with the dashboard site as the default site, so every module
    registers its screens with ``@admin.register`` and gets the dashboard's role checks."""

    default_site = "apps.accounts.dashboard.site.DashboardSite"
