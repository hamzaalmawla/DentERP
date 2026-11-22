"""Routes under /api/v1/. Each module adds one line with its api/urls.py."""

from django.urls import include, path

urlpatterns = [
    path("", include("apps.core.api.urls")),
    path("", include("apps.accounts.api.urls")),
    path("", include("apps.setup.api.urls")),
    path("", include("apps.academics.api.urls")),
    path("", include("apps.patients.api.urls")),
    path("", include("apps.diagnosis.api.urls")),
    path("", include("apps.referrals.api.urls")),
    path("", include("apps.workcards.api.urls")),
    path("", include("apps.media.api.urls")),
    path("", include("apps.scheduling.api.urls")),
    path("", include("apps.maintenance.api.urls")),
    path("", include("apps.notifications.api.urls")),
    path("", include("apps.reports.api.urls")),
]
