"""Work card, case, step and approvals endpoints (design section 7). Placeholders until P1.6
builds them (501). Lab cases (``POST /cases/``) are deferred and not planned here."""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

from apps.accounts.api.permissions import HasAnyRole, IsStudent, IsSupervisor, RoleCode
from apps.core.api.placeholders import Planned, planned_view

StudentOrSupervisor = HasAnyRole(RoleCode.STUDENT, RoleCode.SUPERVISOR)

WorkCardListView = planned_view(
    "workcards",
    prompt="P1.6",
    get=Planned(
        StudentOrSupervisor,
        "Work cards with progress (mine, or in my scope)",
        operation_id="workcards_list",
    ),
)

WorkCardDetailView = planned_view(
    "workcards",
    prompt="P1.6",
    get=Planned(StudentOrSupervisor, "A work card with its cases and progress per case type"),
)

CaseDetailView = planned_view(
    "cases", prompt="P1.6", get=Planned(StudentOrSupervisor, "A case with its steps")
)

CaseCompleteView = planned_view(
    "cases",
    prompt="P1.6",
    post=Planned(IsSupervisor, "Confirm the case is complete (closes the referral)"),
)

StepSubmitView = planned_view(
    "steps", prompt="P1.6", post=Planned(IsStudent, "Mark a step done with a note and photo ids")
)

StepApproveView = planned_view(
    "steps", prompt="P1.6", post=Planned(IsSupervisor, "Grade and approve a submitted step")
)

StepReturnView = planned_view(
    "steps", prompt="P1.6", post=Planned(IsSupervisor, "Return a submitted step with a comment")
)

ApprovalsView = planned_view(
    "approvals",
    prompt="P1.6",
    get=Planned(
        IsSupervisor,
        "One queue of the diagnoses and steps waiting for me",
        parameters=[
            OpenApiParameter("clinic", OpenApiTypes.INT),
            OpenApiParameter("type", OpenApiTypes.STR, enum=["diagnosis", "step"]),
        ],
    ),
)
