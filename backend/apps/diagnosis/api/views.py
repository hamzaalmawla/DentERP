"""Diagnosis endpoints (design section 7). Placeholders until P1.4 builds them (501)."""

from apps.accounts.api.permissions import HasAnyRole, IsStudent, IsSupervisor, RoleCode
from apps.core.api.placeholders import Planned, planned_view

DiagnosisListView = planned_view(
    "diagnoses",
    prompt="P1.4",
    post=Planned(IsStudent, "Start a diagnosis draft for an assigned patient"),
)

DiagnosisDetailView = planned_view(
    "diagnoses",
    prompt="P1.4",
    get=Planned(
        HasAnyRole(RoleCode.STUDENT, RoleCode.SUPERVISOR),
        "A diagnosis with all F1 sections (supervisors read it to review)",
    ),
    patch=Planned(IsStudent, "Edit a draft (all F1 sections in one nested body)"),
)

DiagnosisSubmitView = planned_view(
    "diagnoses", prompt="P1.4", post=Planned(IsStudent, "Send the diagnosis to a supervisor")
)

DiagnosisApproveView = planned_view(
    "diagnoses", prompt="P1.4", post=Planned(IsSupervisor, "Approve a submitted diagnosis")
)

DiagnosisReturnView = planned_view(
    "diagnoses",
    prompt="P1.4",
    post=Planned(IsSupervisor, "Return a submitted diagnosis with a comment"),
)
