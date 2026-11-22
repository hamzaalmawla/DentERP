"""Notifications endpoints (design section 7). Placeholders until P1.10 builds them (501)."""

from apps.accounts.api.permissions import AnyRole
from apps.core.api.placeholders import Planned, planned_view

NotificationListView = planned_view(
    "notifications",
    prompt="P1.10",
    get=Planned(AnyRole, "My notifications, newest first, with the unread count"),
)

NotificationReadView = planned_view(
    "notifications",
    prompt="P1.10",
    post=Planned(AnyRole, "Mark notifications as read (by ids, or all)"),
)
