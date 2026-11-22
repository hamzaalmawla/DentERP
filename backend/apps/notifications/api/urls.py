"""Notifications routes under /api/v1/ (design section 7)."""

from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("notifications/", views.NotificationListView.as_view(), name="notification-list"),
    path("notifications/read/", views.NotificationReadView.as_view(), name="notification-read"),
]
