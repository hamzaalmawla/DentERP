"""Scheduling routes under /api/v1/ (design section 7)."""

from django.urls import path

from . import views

app_name = "scheduling"

urlpatterns = [
    path("schedule/", views.ScheduleView.as_view(), name="schedule"),
    path("clinics/<int:pk>/today/", views.ClinicTodayView.as_view(), name="clinic-today"),
    path("attendance/", views.AttendanceView.as_view(), name="attendance"),
]
