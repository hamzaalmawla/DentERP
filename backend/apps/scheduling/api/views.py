"""Scheduling endpoints (design section 7). Placeholders until P1.8 builds them (501)."""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

from apps.accounts.api.permissions import HasAnyRole, IsSupervisor, RoleCode
from apps.core.api.placeholders import Planned, planned_view

ScheduleView = planned_view(
    "scheduling",
    prompt="P1.8",
    get=Planned(
        HasAnyRole(RoleCode.STUDENT, RoleCode.SUPERVISOR),
        "My chairs and sessions for the coming days",
        parameters=[OpenApiParameter("date", OpenApiTypes.DATE)],
    ),
)

ClinicTodayView = planned_view(
    "scheduling",
    prompt="P1.8",
    get=Planned(IsSupervisor, "The clinic's chair by session grid with students and attendance"),
)

AttendanceView = planned_view(
    "scheduling", prompt="P1.8", post=Planned(IsSupervisor, "Mark attendance in bulk")
)
