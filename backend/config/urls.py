from django.contrib import admin
from django.urls import include, path

from config.health import health

urlpatterns = [
    path("health/", health, name="health"),
    path("api/v1/", include("config.api_v1")),
    path("dashboard/", admin.site.urls),
    # The dashboard's language switch (set_language).
    path("i18n/", include("django.conf.urls.i18n")),
]
