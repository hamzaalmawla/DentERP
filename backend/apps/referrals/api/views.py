"""Referrals endpoints (design section 7). Placeholders until P1.7 builds them (501)."""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

from apps.accounts.api.permissions import IsSupervisor
from apps.core.api.placeholders import Planned, planned_view

ReferralListView = planned_view(
    "referrals",
    prompt="P1.7",
    get=Planned(
        IsSupervisor,
        "My clinics' referral inbox (in) or sent list (out)",
        parameters=[
            OpenApiParameter("direction", OpenApiTypes.STR, enum=["in", "out"]),
            OpenApiParameter("status", OpenApiTypes.STR),
        ],
    ),
    post=Planned(IsSupervisor, "Refer plan items of an approved diagnosis to a clinic"),
)

ReferralAcceptView = planned_view(
    "referrals", prompt="P1.7", post=Planned(IsSupervisor, "Accept a referral to my clinic")
)

ReferralRejectView = planned_view(
    "referrals", prompt="P1.7", post=Planned(IsSupervisor, "Reject a referral with a reason")
)

ReferralAssignView = planned_view(
    "referrals",
    prompt="P1.7",
    post=Planned(IsSupervisor, "Assign an accepted referral to an eligible student"),
)

ReferralEligibleStudentsView = planned_view(
    "referrals",
    prompt="P1.7",
    get=Planned(IsSupervisor, "Students allowed for this referral, with their progress"),
)
