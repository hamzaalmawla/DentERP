"""Maintenance endpoints (design section 7). Placeholders until P1.9 builds them (501).

``GET /clinics/?with=chair_status`` is served by setup's clinic list (chair status is setup
data); see docs/contracts.md.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

from apps.accounts.api.permissions import HasAnyRole, IsTechnician, RoleCode
from apps.core.api.placeholders import Planned, planned_view

TechnicianOrSupervisor = HasAnyRole(RoleCode.TECHNICIAN, RoleCode.SUPERVISOR)

RoundListView = planned_view(
    "maintenance",
    prompt="P1.9",
    post=Planned(IsTechnician, "Submit a morning or afternoon round with every chair check"),
)

TicketListView = planned_view(
    "maintenance",
    prompt="P1.9",
    get=Planned(
        TechnicianOrSupervisor,
        "Fault tickets, oldest open first",
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR),
            OpenApiParameter("clinic", OpenApiTypes.INT),
        ],
    ),
    post=Planned(TechnicianOrSupervisor, "Report a fault on a chair"),
)

TicketStartView = planned_view(
    "maintenance", prompt="P1.9", post=Planned(IsTechnician, "Start work on an open ticket")
)

TicketExternalView = planned_view(
    "maintenance",
    prompt="P1.9",
    post=Planned(IsTechnician, "Send the repair outside, with a note"),
)

TicketResolveView = planned_view(
    "maintenance",
    prompt="P1.9",
    post=Planned(IsTechnician, "Resolve a ticket with a repair note"),
)

ChairStatusView = planned_view(
    "maintenance",
    prompt="P1.9",
    post=Planned(IsTechnician, "Put a chair in or out of service, with a reason"),
)

ChairHistoryView = planned_view(
    "maintenance",
    prompt="P1.9",
    get=Planned(IsTechnician, "A chair's status changes, rounds and tickets"),
)
