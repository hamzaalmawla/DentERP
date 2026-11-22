"""Setup endpoints (design section 7). Placeholders until P1.1 builds them (501)."""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

from apps.accounts.api.permissions import AnyRole
from apps.core.api.placeholders import Planned, planned_view

LookupsView = planned_view(
    "lookups",
    prompt="P1.1",
    get=Planned(
        AnyRole,
        "Every lookup list in one call, in the request language, with its version (ETag)",
    ),
)

ClinicListView = planned_view(
    "clinics",
    prompt="P1.1",
    get=Planned(
        AnyRole,
        "Clinics; with=chair_status adds the chairs in and out of service",
        parameters=[
            OpenApiParameter("type", OpenApiTypes.STR, enum=["diagnosis", "treatment", "lab"]),
            OpenApiParameter("with", OpenApiTypes.STR, enum=["chair_status"]),
        ],
    ),
)
