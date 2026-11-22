"""Patients routes under /api/v1/ (design section 7)."""

from django.urls import path

from . import views

app_name = "patients"

urlpatterns = [
    path("patients/", views.PatientListView.as_view(), name="patient-list"),
    path("patients/<int:pk>/", views.PatientDetailView.as_view(), name="patient-detail"),
    path(
        "patients/<int:pk>/transfer/",
        views.PatientTransferView.as_view(),
        name="patient-transfer",
    ),
    path("diagnosis-queue/", views.DiagnosisQueueView.as_view(), name="queue-list"),
    path(
        "diagnosis-queue/<int:pk>/assign/",
        views.DiagnosisQueueAssignView.as_view(),
        name="queue-assign",
    ),
]
