"""Routes under /api/v1/. Each module adds one line with its api/urls.py."""

from django.urls import include, path

urlpatterns = [
    path("", include("apps.core.api.urls")),
]
