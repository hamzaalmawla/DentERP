"""Diagnosis routes under /api/v1/ (design section 7)."""

from django.urls import path

from . import views

app_name = "diagnosis"

urlpatterns = [
    path("diagnoses/", views.DiagnosisListView.as_view(), name="diagnosis-list"),
    path("diagnoses/<int:pk>/", views.DiagnosisDetailView.as_view(), name="diagnosis-detail"),
    path(
        "diagnoses/<int:pk>/submit/",
        views.DiagnosisSubmitView.as_view(),
        name="diagnosis-submit",
    ),
    path(
        "diagnoses/<int:pk>/approve/",
        views.DiagnosisApproveView.as_view(),
        name="diagnosis-approve",
    ),
    path(
        "diagnoses/<int:pk>/return/",
        views.DiagnosisReturnView.as_view(),
        name="diagnosis-return",
    ),
]
