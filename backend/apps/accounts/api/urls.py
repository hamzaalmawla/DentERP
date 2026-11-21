"""Accounts routes under /api/v1/ (design section 7)."""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/refresh/", views.RefreshView.as_view(), name="refresh"),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    path("me/", views.MeView.as_view(), name="me"),
    path("me/password/", views.MyPasswordView.as_view(), name="me-password"),
    path("me/devices/", views.MyDevicesView.as_view(), name="me-devices"),
]
