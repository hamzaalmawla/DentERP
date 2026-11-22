"""Setup routes under /api/v1/ (design section 7)."""

from django.urls import path

from . import views

app_name = "setup"

urlpatterns = [
    path("lookups/", views.LookupsView.as_view(), name="lookups"),
    path("clinics/", views.ClinicListView.as_view(), name="clinics"),
]
