"""Maintenance routes under /api/v1/ (design section 7)."""

from django.urls import path

from . import views

app_name = "maintenance"

urlpatterns = [
    path("rounds/", views.RoundListView.as_view(), name="round-list"),
    path("tickets/", views.TicketListView.as_view(), name="ticket-list"),
    path("tickets/<int:pk>/start/", views.TicketStartView.as_view(), name="ticket-start"),
    path("tickets/<int:pk>/external/", views.TicketExternalView.as_view(), name="ticket-external"),
    path("tickets/<int:pk>/resolve/", views.TicketResolveView.as_view(), name="ticket-resolve"),
    path("chairs/<int:pk>/status/", views.ChairStatusView.as_view(), name="chair-status"),
    path("chairs/<int:pk>/history/", views.ChairHistoryView.as_view(), name="chair-history"),
]
